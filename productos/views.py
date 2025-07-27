
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch, Q, F, Sum
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import ProductoTerminado, ComponenteProducto, EstadoOrden, OrdenProduccion, Reportes, SectorAsignado, CategoriaProductoTerminado, LoteProductoTerminado
from core.common.utils import es_admin, es_admin_o_rol
from .forms import OrdenProduccionUpdateForm, ReporteProduccionForm
from depositos.models import Deposito
from insumos.models import Insumo, Orden
import logging
logger = logging.getLogger(__name__)

# --- Vistas de Producción ---
@login_required
def produccion_lista_op_view(request):
    ESTADOS_FINALIZADOS = ["Completada", "Cancelada"]
    base_query = OrdenProduccion.objects.select_related(
        "producto_a_producir__categoria",
        "orden_venta_origen__cliente",
        "estado_op",
        "sector_asignado_op",
    ).prefetch_related(
        Prefetch(
            "reportes_incidencia",
            queryset=Reportes.objects.filter(resuelto=False).select_related(
                "reportado_por", "sector_reporta"
            ),
            to_attr="reportes_abiertos",
        )
    )
    ops_activas = base_query.exclude(
        estado_op__nombre__in=ESTADOS_FINALIZADOS
    ).order_by("fecha_solicitud")
    ops_finalizadas = base_query.filter(
        estado_op__nombre__in=ESTADOS_FINALIZADOS
    ).order_by("-fecha_solicitud")
    context = {
        "ops_activas_list": ops_activas,
        "ops_finalizadas_list": ops_finalizadas,
        "titulo_seccion": "Listado de Órdenes de Producción",
    }
    return render(request, "produccion/produccion_lista_op.html", context)

@login_required
def planificacion_produccion_view(request):
    if request.method == "POST":
        op_id_a_actualizar = request.POST.get("op_id")
        try:
            op_a_actualizar = get_object_or_404(OrdenProduccion, id=op_id_a_actualizar)
            form = OrdenProduccionUpdateForm(request.POST, instance=op_a_actualizar)
            sector_id = request.POST.get("sector_asignado_op")
            fecha_inicio_p = request.POST.get("fecha_inicio_planificada")
            fecha_fin_p = request.POST.get("fecha_fin_planificada")
            if sector_id:
                op_a_actualizar.sector_asignado_op_id = sector_id
            if fecha_inicio_p:
                op_a_actualizar.fecha_inicio_planificada = fecha_inicio_p
            if fecha_fin_p:
                op_a_actualizar.fecha_fin_planificada = fecha_fin_p
            op_a_actualizar.save()
            messages.success(request, f"Planificación para OP {op_a_actualizar.numero_op} actualizada.")
        except Exception as e:
            messages.error(request, f"Error al actualizar la planificación: {e}")
        return redirect("productos:planificacion_produccion")
    estados_finales = ["Completada", "Cancelada"]
    ops_para_planificar = (
        OrdenProduccion.objects.exclude(estado_op__nombre__in=estados_finales)
        .select_related("producto_a_producir", "orden_venta_origen__cliente", "estado_op", "sector_asignado_op")
        .order_by("estado_op__id", "fecha_solicitud")
    )
    sectores = SectorAsignado.objects.all().order_by("nombre")
    context = {
        "ops_para_planificar_list": ops_para_planificar,
        "sectores_list": sectores,
        "titulo_seccion": "Planificación de Órdenes de Producción",
    }
    return render(request, "produccion/planificacion.html", context)

@login_required
@require_POST
@transaction.atomic
def solicitar_insumos_op_view(request, op_id):
    op = get_object_or_404(OrdenProduccion.objects.select_related("estado_op", "orden_venta_origen", "producto_a_producir"), id=op_id)
    estado_op_anterior_obj = op.estado_op
    estado_actual_op_nombre = op.estado_op.nombre.lower() if op.estado_op else ""
    if estado_actual_op_nombre not in ["pendiente", "planificada"]:
        messages.error(request, f"La OP {op.numero_op} no está en un estado válido para solicitar insumos (actual: {op.get_estado_op_display()}).")
        return redirect("productos:produccion_detalle_op", op_id=op.id)
    try:
        estado_insumos_solicitados_op = EstadoOrden.objects.get(nombre__iexact="Insumos Solicitados")
        op.estado_op = estado_insumos_solicitados_op
        op.save(update_fields=["estado_op"])
        messages.success(request, f"Solicitud de insumos para OP {op.numero_op} enviada a Depósito.")
    except EstadoOrden.DoesNotExist:
        messages.error(request, "Error crítico: El estado 'Insumos Solicitados' no está configurado.")
    except Exception as e:
        messages.error(request, f"Error al solicitar insumos: {str(e)}")
    return redirect("productos:produccion_detalle_op", op_id=op.id)

@login_required
@transaction.atomic
def produccion_detalle_op_view(request, op_id):
    op = get_object_or_404(OrdenProduccion.objects.select_related("producto_a_producir__categoria", "orden_venta_origen__cliente", "estado_op", "sector_asignado_op").prefetch_related("orden_venta_origen__ops_generadas__estado_op", "producto_a_producir__componentes_requeridos__insumo"), id=op_id)
    estado_op_anterior_obj = op.estado_op
    insumos_necesarios_data = []
    todos_los_insumos_disponibles = True
    if op.producto_a_producir:
        componentes_requeridos = op.producto_a_producir.componentes_requeridos.all()
        if not componentes_requeridos:
            todos_los_insumos_disponibles = False
        for comp in componentes_requeridos:
            cantidad_total_requerida_para_op = comp.cantidad_necesaria * op.cantidad_a_producir
            suficiente = comp.insumo.stock >= cantidad_total_requerida_para_op
            if not suficiente:
                todos_los_insumos_disponibles = False
            insumos_necesarios_data.append({
                "insumo_descripcion": comp.insumo.descripcion,
                "cantidad_por_unidad_pt": comp.cantidad_necesaria,
                "cantidad_total_requerida_op": cantidad_total_requerida_para_op,
                "stock_actual_insumo": comp.insumo.stock,
                "suficiente_stock": suficiente,
                "insumo_id": comp.insumo.id,
            })
    else:
        todos_los_insumos_disponibles = False
    puede_solicitar_insumos = False
    mostrar_boton_reportar = False
    estado_op_queryset_para_form = EstadoOrden.objects.all().order_by("nombre")
    ESTADO_OP_PENDIENTE_LOWER = "pendiente"
    ESTADO_OP_PLANIFICADA_LOWER = "planificada"
    ESTADO_OP_INSUMOS_SOLICITADOS_LOWER = "insumos solicitados"
    ESTADO_OP_INSUMOS_RECIBIDOS_LOWER = "insumos recibidos"
    ESTADO_OP_PRODUCCION_INICIADA_LOWER = "producción iniciada"
    ESTADO_OP_EN_PROCESO_LOWER = "en proceso"
    ESTADO_OP_PAUSADA_LOWER = "pausada"
    NOMBRE_ESTADO_OP_COMPLETADA_CONST = "Completada"
    ESTADO_OP_COMPLETADA_LOWER = NOMBRE_ESTADO_OP_COMPLETADA_CONST.lower()
    ESTADO_OP_CANCELADA_LOWER = "cancelada"
    if op.estado_op:
        estado_actual_nombre_lower = op.estado_op.nombre.lower()
        estado_actual_nombre_original = op.estado_op.nombre
        nombres_permitidos_dropdown = [estado_actual_nombre_original]
        if estado_actual_nombre_lower in [ESTADO_OP_PENDIENTE_LOWER, ESTADO_OP_PLANIFICADA_LOWER] and op.sector_asignado_op:
            puede_solicitar_insumos = True
        elif estado_actual_nombre_lower == ESTADO_OP_INSUMOS_SOLICITADOS_LOWER:
            nombres_permitidos_dropdown.extend(["Pausada", "Cancelada"])
        elif estado_actual_nombre_lower == ESTADO_OP_INSUMOS_RECIBIDOS_LOWER:
            nombres_permitidos_dropdown.extend(["Producción Iniciada", "Pausada", "Cancelada"])
        elif estado_actual_nombre_lower == ESTADO_OP_PRODUCCION_INICIADA_LOWER:
            nombres_permitidos_dropdown.extend(["En Proceso", "Pausada", "Completada", "Cancelada"])
        elif estado_actual_nombre_lower == ESTADO_OP_EN_PROCESO_LOWER:
            nombres_permitidos_dropdown.extend(["Pausada", "Completada", "Cancelada"])
        elif estado_actual_nombre_lower == ESTADO_OP_PAUSADA_LOWER:
            nombres_permitidos_dropdown.extend(["Cancelada"])
            if EstadoOrden.objects.filter(nombre__iexact=ESTADO_OP_INSUMOS_RECIBIDOS_LOWER).exists():
                nombres_permitidos_dropdown.append("Insumos Recibidos")
            if EstadoOrden.objects.filter(nombre__iexact=ESTADO_OP_PRODUCCION_INICIADA_LOWER).exists():
                nombres_permitidos_dropdown.append("Producción Iniciada")
            if EstadoOrden.objects.filter(nombre__iexact=ESTADO_OP_PENDIENTE_LOWER).exists():
                nombres_permitidos_dropdown.append("Pendiente")
        if estado_actual_nombre_lower not in [ESTADO_OP_COMPLETADA_LOWER, ESTADO_OP_CANCELADA_LOWER]:
            mostrar_boton_reportar = True
        q_permitidos = Q()
        for n in list(set(nombres_permitidos_dropdown)):
            q_permitidos |= Q(nombre__iexact=n)
        if q_permitidos:
            estado_op_queryset_para_form = EstadoOrden.objects.filter(q_permitidos).order_by("nombre")
        elif op.estado_op:
            estado_op_queryset_para_form = EstadoOrden.objects.filter(id=op.estado_op.id)
    if request.method == "POST":
        form_update = OrdenProduccionUpdateForm(request.POST, instance=op, estado_op_queryset=estado_op_queryset_para_form)
        if form_update.is_valid():
            nuevo_estado_op_obj = form_update.cleaned_data.get("estado_op")
            op_actualizada = form_update.save(commit=False)
            se_esta_completando_op_ahora = False
            if nuevo_estado_op_obj and nuevo_estado_op_obj.nombre.lower() == ESTADO_OP_COMPLETADA_LOWER:
                if not estado_op_anterior_obj or estado_op_anterior_obj.nombre.lower() != ESTADO_OP_COMPLETADA_LOWER:
                    se_esta_completando_op_ahora = True
                    op_actualizada.fecha_fin_real = timezone.now() if not op_actualizada.fecha_fin_real else op_actualizada.fecha_fin_real
            if se_esta_completando_op_ahora:
                producto_terminado_obj = op_actualizada.producto_a_producir
                cantidad_producida = op_actualizada.cantidad_a_producir
                if producto_terminado_obj and cantidad_producida > 0:
                    deposito_central = Deposito.objects.filter(nombre__iexact="Depósito Central").first()
                    if deposito_central:
                        producto_terminado_obj.agregar_stock(cantidad_producida, deposito_central)
                        logger.info(f"Stock de '{producto_terminado_obj.descripcion}' incrementado en {cantidad_producida} en '{deposito_central.nombre}'.")
                    else:
                        logger.error("No se encontró el Depósito Central para registrar el stock producido.")
                    LoteProductoTerminado.objects.create(
                        producto=producto_terminado_obj,
                        op_asociada=op_actualizada,
                        cantidad=cantidad_producida,
                    )
                    messages.info(request, f"Lote de {cantidad_producida} x '{producto_terminado_obj.descripcion}' generado y stock actualizado.")
            op_actualizada.save()
            messages.success(request, f"Orden de Producción {op_actualizada.numero_op} actualizada a '{op_actualizada.get_estado_op_display()}'.")
            return redirect("productos:produccion_detalle_op", op_id=op_actualizada.id)
        else:
            messages.error(request, "Error al actualizar la OP. Por favor, revise los datos del formulario.")
    else:
        form_update = OrdenProduccionUpdateForm(instance=op, estado_op_queryset=estado_op_queryset_para_form)
    estados_activos_para_reportar = ["insumos solicitados", "producción iniciada", "en proceso", "pausada", "producción con problemas"]
    mostrar_boton_reportar = op.estado_op and op.estado_op.nombre.lower() in estados_activos_para_reportar
    context = {
        "op": op,
        "insumos_necesarios_list": insumos_necesarios_data,
        "form_update_op": form_update,
        "todos_los_insumos_disponibles_variable_de_contexto": todos_los_insumos_disponibles,
        "puede_solicitar_insumos": puede_solicitar_insumos,
        "mostrar_boton_reportar": mostrar_boton_reportar,
        "titulo_seccion": f"Detalle OP: {op.numero_op}",
    }
    return render(request, "produccion/produccion_detalle_op.html", context)

@login_required
def reportes_produccion_view(request, reporte_id=None, resolver=False):
    if resolver and reporte_id and request.method == "POST":
        reporte_a_resolver = get_object_or_404(Reportes, id=reporte_id)
        if not reporte_a_resolver.resuelto:
            reporte_a_resolver.resuelto = True
            reporte_a_resolver.fecha_resolucion = timezone.now()
            reporte_a_resolver.save()
            op_asociada = reporte_a_resolver.orden_produccion_asociada
            if op_asociada and op_asociada.estado_op and op_asociada.estado_op.nombre in ["Pausada", "Producción con Problemas"]:
                try:
                    estado_reanudado = EstadoOrden.objects.get(nombre__iexact="En Proceso")
                    op_asociada.estado_op = estado_reanudado
                    op_asociada.save()
                    messages.success(request, f"El problema del reporte {reporte_a_resolver.n_reporte} ha sido resuelto y la OP {op_asociada.numero_op} ha sido reanudada.")
                except EstadoOrden.DoesNotExist:
                    messages.warning(request, f"Reporte {reporte_a_resolver.n_reporte} resuelto, pero no se encontró el estado 'En Proceso' para reanudar la OP.")
            else:
                messages.success(request, f"El reporte {reporte_a_resolver.n_reporte} ha sido marcado como resuelto.")
        else:
            messages.info(request, "Este reporte ya había sido resuelto anteriormente.")
        return redirect("productos:reportes_produccion")
    reportes_abiertos = Reportes.objects.filter(resuelto=False).select_related("orden_produccion_asociada", "reportado_por", "sector_reporta").order_by("-fecha")
    reportes_resueltos = Reportes.objects.filter(resuelto=True).select_related("orden_produccion_asociada", "reportado_por", "sector_reporta").order_by("-fecha_resolucion")
    context = {
        "reportes_abiertos": reportes_abiertos,
        "reportes_resueltos": reportes_resueltos,
        "titulo_seccion": "Reportes de Producción",
    }
    return render(request, "produccion/reportes.html", context)

@login_required
@transaction.atomic
def crear_reporte_produccion_view(request, op_id):
    orden_produccion = get_object_or_404(OrdenProduccion, id=op_id)
    if request.method == "POST":
        form = ReporteProduccionForm(request.POST, orden_produccion=orden_produccion)
        if form.is_valid():
            reporte = form.save(commit=False)
            reporte.orden_produccion_asociada = orden_produccion
            reporte.reportado_por = request.user
            reporte.fecha = timezone.now()
            reporte.n_reporte = generar_siguiente_numero_documento(Reportes, 'RP', 'n_reporte')
            reporte.save()
            messages.success(request, f"Reporte '{reporte.n_reporte}' creado exitosamente para la OP {orden_produccion.numero_op}.")
            return redirect("productos:reportes_produccion")
        else:
            messages.error(request, "Por favor, corrija los errores en el formulario de reporte.")
    else:
        form = ReporteProduccionForm(orden_produccion=orden_produccion)
    context = {
        "form_reporte": form,
        "orden_produccion": orden_produccion,
        "titulo_seccion": f"Crear Reporte para OP: {orden_produccion.numero_op}",
    }
    return render(request, "produccion/crear_reporte.html", context)
