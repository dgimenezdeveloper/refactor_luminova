import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout as auth_logout_function
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import PasswordChangeForm

# Django Contrib Imports
from django.contrib.auth.models import Group, Permission, User
from django.db import IntegrityError as DjangoIntegrityError
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Prefetch, ProtectedError, Q, Sum

# Django Core Imports
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt  # Usar con precaución
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# ReportLab (Third-party for PDF generation)
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from Proyecto_LUMINOVA import settings

# Local Application Imports (Forms)
from .forms import (
    ClienteForm,
    FacturaForm,
    ItemOrdenVentaFormSet,
    ItemOrdenVentaFormSetCreacion,
    OrdenCompraForm,
    OrdenProduccionUpdateForm,
    OrdenVentaForm,
    PermisosRolForm,
    ProveedorForm,
    ReporteProduccionForm,
    RolForm,
)

# Local Application Imports (Models)
from .models import (
    AuditoriaAcceso,
    CategoriaInsumo,
    CategoriaProductoTerminado,
    Cliente,
    ComponenteProducto,
    EstadoOrden,
    Fabricante,
    Factura,
    HistorialOV,
    Insumo,
    ItemOrdenVenta,
    LoteProductoTerminado,
    OfertaProveedor,
    Orden,
    OrdenProduccion,
    OrdenVenta,
    PasswordChangeRequired,
    ProductoTerminado,
    Proveedor,
    Reportes,
    RolDescripcion,
    SectorAsignado,
)
from .signals import get_client_ip

from .services.document_services import generar_siguiente_numero_documento
from .services.pdf_services import generar_pdf_factura
from .utils import es_admin, es_admin_o_rol

logger = logging.getLogger(__name__)

# --- PRODUCCIÓN VIEWS ---
def proveedor_create_view(request):
    if not request.user.is_authenticated:
        return redirect("App_LUMINOVA:login")

    if request.method == "POST":
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save()
            messages.success(
                request, f"Proveedor {proveedor.nombre} creado exitosamente."
            )
            return redirect("App_LUMINOVA:proveedor_list")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request, f"{form.fields[field].label or field}: {error}"
                    )
    else:
        form = ProveedorForm()

    context = {
        "form": form,
        "titulo_seccion": "Crear Proveedor",
    }
    return render(request, "ventas/proveedores/proveedor_crear.html", context)


@login_required
def produccion_lista_op_view(request):
    """
    Muestra el listado de Órdenes de Producción, separadas en pestañas
    para "Activas" y "Finalizadas" (Completadas/Canceladas).
    """

    # Estados que consideramos "finalizados" y que irán a la pestaña de historial.
    ESTADOS_FINALIZADOS = ["Completada", "Cancelada"]

    # Creamos una consulta base para no repetir el código.
    # Esta consulta ya incluye las optimizaciones de select_related y prefetch_related.
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
            to_attr="reportes_abiertos",  # El resultado se guardará en op.reportes_abiertos
        )
    )

    # 1. Lista de OPs "Activas": todas aquellas cuyo estado NO está en la lista de finalizados.
    #    Se ordenan por las más antiguas primero para darles prioridad.
    ops_activas = base_query.exclude(
        estado_op__nombre__in=ESTADOS_FINALIZADOS
    ).order_by("fecha_solicitud")

    # 2. Lista de OPs "Finalizadas": todas aquellas cuyo estado SÍ está en la lista.
    #    Se ordenan por las más recientes primero para ver lo último que se terminó.
    ops_finalizadas = base_query.filter(
        estado_op__nombre__in=ESTADOS_FINALIZADOS
    ).order_by("-fecha_solicitud")

    context = {
        "ops_activas_list": ops_activas,
        "ops_finalizadas_list": ops_finalizadas,
        "titulo_seccion": "Listado de Órdenes de Producción",
        # No es necesario pasar el form_update_op aquí, ya que no se usa en la vista de lista.
    }

    return render(request, "produccion/produccion_lista_op.html", context)


@login_required
def planificacion_produccion_view(request):
    # if not es_admin_o_rol(request.user, ['produccion', 'administrador']):
    #     messages.error(request, "Acceso denegado.")
    #     return redirect('App_LUMINOVA:dashboard')

    if request.method == "POST":
        op_id_a_actualizar = request.POST.get("op_id")
        try:
            op_a_actualizar = get_object_or_404(OrdenProduccion, id=op_id_a_actualizar)

            # Usamos un formulario para validar y limpiar los datos
            form = OrdenProduccionUpdateForm(request.POST, instance=op_a_actualizar)

            # Solo nos interesan ciertos campos del formulario en esta vista
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
            messages.success(
                request,
                f"Planificación para OP {op_a_actualizar.numero_op} actualizada.",
            )
        except Exception as e:
            messages.error(request, f"Error al actualizar la planificación: {e}")

        return redirect("App_LUMINOVA:planificacion_produccion")

    # --- LÓGICA GET MEJORADA ---
    # Obtener todas las OPs que no estén en un estado final
    estados_finales = ["Completada", "Cancelada"]
    ops_para_planificar = (
        OrdenProduccion.objects.exclude(estado_op__nombre__in=estados_finales)
        .select_related(
            "producto_a_producir",
            "orden_venta_origen__cliente",
            "estado_op",
            "sector_asignado_op",
        )
        .order_by("estado_op__id", "fecha_solicitud")
    )  # Ordenar por estado y luego por fecha

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
    op = get_object_or_404(
        OrdenProduccion.objects.select_related(
            "estado_op", "orden_venta_origen", "producto_a_producir"
        ),
        id=op_id,
    )
    estado_op_anterior_obj = op.estado_op

    estado_actual_op_nombre = op.estado_op.nombre.lower() if op.estado_op else ""
    if estado_actual_op_nombre not in ["pendiente", "planificada"]:
        messages.error(
            request,
            f"La OP {op.numero_op} no está en un estado válido para solicitar insumos (actual: {op.get_estado_op_display()}).",
        )
        return redirect("App_LUMINOVA:produccion_detalle_op", op_id=op.id)

    try:
        estado_insumos_solicitados_op = EstadoOrden.objects.get(
            nombre__iexact="Insumos Solicitados"
        )

        # Log de cambio de estado de OP antes de guardar
        if (
            op.orden_venta_origen
            and estado_op_anterior_obj != estado_insumos_solicitados_op
        ):
            descripcion_op = (
                f"La OP {op.numero_op} ('{op.producto_a_producir.descripcion}') cambió su estado "
                f"de '{estado_op_anterior_obj.nombre if estado_op_anterior_obj else 'N/A'}' "
                f"a '{estado_insumos_solicitados_op.nombre}'."
            )
            HistorialOV.objects.create(
                orden_venta=op.orden_venta_origen,
                descripcion=descripcion_op,
                tipo_evento="Cambio Estado OP",
                realizado_por=request.user,
            )

        op.estado_op = estado_insumos_solicitados_op
        op.save(update_fields=["estado_op"])
        messages.success(
            request, f"Solicitud de insumos para OP {op.numero_op} enviada a Depósito."
        )

        # Actualizar estado de la OV si corresponde
        if op.orden_venta_origen:
            orden_venta_asociada = op.orden_venta_origen
            if orden_venta_asociada.estado in ["PENDIENTE", "CONFIRMADA"]:
                estado_ov_anterior_str = orden_venta_asociada.get_estado_display()
                orden_venta_asociada.estado = "INSUMOS_SOLICITADOS"
                orden_venta_asociada.save(update_fields=["estado"])

                # Log de cambio de estado de OV
                descripcion_ov = f"Estado de la OV cambió de '{estado_ov_anterior_str}' a 'Insumos Solicitados'."
                HistorialOV.objects.create(
                    orden_venta=orden_venta_asociada,
                    descripcion=descripcion_ov,
                    tipo_evento="Cambio Estado OV",
                    realizado_por=request.user,
                )

                messages.info(
                    request,
                    f"Estado de OV {orden_venta_asociada.numero_ov} actualizado.",
                )

    except EstadoOrden.DoesNotExist:
        messages.error(
            request,
            "Error crítico: El estado 'Insumos Solicitados' no está configurado.",
        )
    except Exception as e:
        messages.error(request, f"Error al solicitar insumos: {str(e)}")

    return redirect("App_LUMINOVA:produccion_detalle_op", op_id=op.id)


@login_required
@transaction.atomic
def produccion_detalle_op_view(request, op_id):
    # Restaurar prefetch de componentes para que la vista funcione correctamente
    op = get_object_or_404(
        OrdenProduccion.objects.select_related(
            "producto_a_producir__categoria",
            "orden_venta_origen__cliente",
            "estado_op",
            "sector_asignado_op",
        ).prefetch_related(
            "producto_a_producir__componentes_requeridos__insumo",
        ),
        id=op_id,
    )
    estado_op_anterior_obj = op.estado_op

    insumos_necesarios_data = []
    todos_los_insumos_disponibles = True
    if op.producto_a_producir:
        componentes_requeridos = op.producto_a_producir.componentes_requeridos.all()
        if not componentes_requeridos:
            todos_los_insumos_disponibles = False
        for comp in componentes_requeridos:
            cantidad_total_requerida_para_op = (
                comp.cantidad_necesaria * op.cantidad_a_producir
            )
            suficiente = comp.insumo.stock >= cantidad_total_requerida_para_op
            if not suficiente:
                todos_los_insumos_disponibles = False
            insumos_necesarios_data.append(
                {
                    "insumo_descripcion": comp.insumo.descripcion,
                    "cantidad_por_unidad_pt": comp.cantidad_necesaria,
                    "cantidad_total_requerida_op": cantidad_total_requerida_para_op,
                    "stock_actual_insumo": comp.insumo.stock,
                    "suficiente_stock": suficiente,
                    "insumo_id": comp.insumo.id,
                }
            )
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

        if (
            estado_actual_nombre_lower
            in [ESTADO_OP_PENDIENTE_LOWER, ESTADO_OP_PLANIFICADA_LOWER]
            and op.sector_asignado_op
        ):
            puede_solicitar_insumos = True
        elif estado_actual_nombre_lower == ESTADO_OP_INSUMOS_SOLICITADOS_LOWER:
            nombres_permitidos_dropdown.extend(["Insumos Recibidos", "Producción Iniciada", "Pausada", "Cancelada"])
        elif estado_actual_nombre_lower == ESTADO_OP_INSUMOS_RECIBIDOS_LOWER:
            nombres_permitidos_dropdown.extend(
                ["Producción Iniciada", "Pausada", "Cancelada"]
            )
        elif estado_actual_nombre_lower == ESTADO_OP_PRODUCCION_INICIADA_LOWER:
            nombres_permitidos_dropdown.extend(
                ["En Proceso", "Pausada", "Completada", "Cancelada"]
            )
        elif estado_actual_nombre_lower == ESTADO_OP_EN_PROCESO_LOWER:
            nombres_permitidos_dropdown.extend(["Pausada", "Completada", "Cancelada"])
        elif estado_actual_nombre_lower == ESTADO_OP_PAUSADA_LOWER:
            nombres_permitidos_dropdown.extend(["Cancelada"])
            if EstadoOrden.objects.filter(
                nombre__iexact=ESTADO_OP_INSUMOS_RECIBIDOS_LOWER
            ).exists():
                nombres_permitidos_dropdown.append("Insumos Recibidos")
            if EstadoOrden.objects.filter(
                nombre__iexact=ESTADO_OP_PRODUCCION_INICIADA_LOWER
            ).exists():
                nombres_permitidos_dropdown.append("Producción Iniciada")
            if EstadoOrden.objects.filter(
                nombre__iexact=ESTADO_OP_PENDIENTE_LOWER
            ).exists():
                nombres_permitidos_dropdown.append("Pendiente")

        if estado_actual_nombre_lower not in [
            ESTADO_OP_COMPLETADA_LOWER,
            ESTADO_OP_CANCELADA_LOWER,
        ]:
            mostrar_boton_reportar = True

        q_permitidos = Q()
        for n in list(set(nombres_permitidos_dropdown)):
            q_permitidos |= Q(nombre__iexact=n)
        if q_permitidos:
            estado_op_queryset_para_form = EstadoOrden.objects.filter(
                q_permitidos
            ).order_by("nombre")
        elif op.estado_op:
            estado_op_queryset_para_form = EstadoOrden.objects.filter(
                id=op.estado_op.id
            )

    if request.method == "POST":
        # --- LOGGING Y PROTECCIÓN EXTRA PARA DETECTAR EL ERROR DE 'stock' ---
        if "stock" in request.POST or "stock" in request.GET:
            logger.warning(f"[DEBUG] Se detectó 'stock' en los datos del request: POST={request.POST.get('stock')}, GET={request.GET.get('stock')}")
        form_update = OrdenProduccionUpdateForm(
            request.POST, instance=op, estado_op_queryset=estado_op_queryset_para_form
        )
        if form_update.is_valid():
            nuevo_estado_op_obj = form_update.cleaned_data.get("estado_op")

            # Log de cambio de estado de OP
            if op.orden_venta_origen and estado_op_anterior_obj != nuevo_estado_op_obj:
                descripcion_op = (
                    f"La OP {op.numero_op} ('{op.producto_a_producir.descripcion}') cambió su estado "
                    f"de '{estado_op_anterior_obj.nombre if estado_op_anterior_obj else 'N/A'}' "
                    f"a '{nuevo_estado_op_obj.nombre if nuevo_estado_op_obj else 'N/A'}'."
                )
                HistorialOV.objects.create(
                    orden_venta=op.orden_venta_origen,
                    descripcion=descripcion_op,
                    tipo_evento="Cambio Estado OP",
                    realizado_por=request.user,
                )

            op_actualizada = form_update.save(commit=False)
            se_esta_completando_op_ahora = False
            if (
                nuevo_estado_op_obj
                and nuevo_estado_op_obj.nombre.lower() == ESTADO_OP_COMPLETADA_LOWER
            ):
                if (
                    not estado_op_anterior_obj
                    or estado_op_anterior_obj.nombre.lower()
                    != ESTADO_OP_COMPLETADA_LOWER
                ):
                    se_esta_completando_op_ahora = True
                    op_actualizada.fecha_fin_real = (
                        timezone.now()
                        if not op_actualizada.fecha_fin_real
                        else op_actualizada.fecha_fin_real
                    )

            if se_esta_completando_op_ahora:
                producto_terminado_obj = op_actualizada.producto_a_producir
                cantidad_producida = op_actualizada.cantidad_a_producir
                if producto_terminado_obj and cantidad_producida > 0:
                    try:
                        # 1. Actualizar el stock principal del ProductoTerminado
                        producto_terminado_obj.stock = F("stock") + cantidad_producida
                        producto_terminado_obj.save(update_fields=["stock"])
                        logger.info(
                            f"Stock de '{producto_terminado_obj.descripcion}' incrementado en {cantidad_producida}."
                        )

                        # 2. Crear el lote para registro y envío
                        try:
                            deposito_lote = None
                            if hasattr(producto_terminado_obj, 'deposito_id') and producto_terminado_obj.deposito_id:
                                from .models import Deposito
                                try:
                                    deposito_lote = Deposito.objects.get(id=producto_terminado_obj.deposito_id)
                                    logger.debug(f"Depósito encontrado para el lote: {deposito_lote}")
                                except Exception as e_depo:
                                    logger.error(f"Error buscando depósito para el producto terminado: {e_depo}")
                                    deposito_lote = None
                            # --- PROTECCIÓN: limpiar kwargs de create() ---
                            lote_kwargs = dict(
                                producto=producto_terminado_obj,
                                op_asociada=op_actualizada,
                                cantidad=cantidad_producida,
                                deposito=deposito_lote,
                                enviado=False
                            )
                            # Eliminar cualquier clave 'stock' si accidentalmente llega
                            lote_kwargs.pop('stock', None)
                            logger.debug(f"Creando lote con: {lote_kwargs}")
                            logger.debug(f"Producto objeto: {producto_terminado_obj} (ID: {producto_terminado_obj.id})")
                            logger.debug(f"OP objeto: {op_actualizada} (ID: {op_actualizada.id})")
                            logger.debug(f"Depósito objeto: {deposito_lote}")
                            
                            # NUEVO: Intentar crear paso a paso para identificar el problema
                            with transaction.atomic():
                                logger.debug("Iniciando creación de lote...")
                                lote = LoteProductoTerminado.objects.create(**lote_kwargs)
                                logger.debug(f"Lote creado exitosamente con ID: {lote.id}")
                                
                            logger.info(f"Lote ID {lote.id} creado exitosamente para OP {op_actualizada.numero_op}")
                            messages.info(
                                request,
                                f"Lote de {cantidad_producida} x '{producto_terminado_obj.descripcion}' generado y stock actualizado.",
                            )
                        except Exception as e_lote:
                            logger.error(f"Error detallado al crear lote para OP {op_actualizada.numero_op}: {e_lote}")
                            logger.error(f"Tipo de excepción: {type(e_lote).__name__}")
                            if hasattr(e_lote, 'args'):
                                logger.error(f"Argumentos de la excepción: {e_lote.args}")
                            messages.warning(
                                request,
                                f"Stock actualizado correctamente, pero hubo un problema al crear el lote: {e_lote}",
                            )
                    except Exception as e:
                        logger.error(f"[DEBUG] Error al crear lote para OP {op_actualizada.numero_op}: {e}")
                        logger.error(f"[DEBUG] Tipo de excepción: {type(e).__name__}")
                        if hasattr(e, 'args'):
                            logger.error(f"[DEBUG] Argumentos de la excepción: {e.args}")
                        messages.error(
                            request,
                            f"Error al crear el lote de producción: {e}. Por favor, contacte al administrador.",
                        )
                        # Continuar con el resto del proceso aunque falle la creación del lote

            op_actualizada.save()
            messages.success(
                request,
                f"Orden de Producción {op_actualizada.numero_op} actualizada a '{op_actualizada.get_estado_op_display()}'.",
            )

            if op_actualizada.orden_venta_origen:
                try:
                    orden_venta_asociada = op_actualizada.orden_venta_origen
                    ops_de_la_ov = OrdenProduccion.objects.filter(
                        orden_venta_origen=orden_venta_asociada
                    ).only('id', 'estado_op')

                    total_ops_en_ov = ops_de_la_ov.count()
                    count_completada = ops_de_la_ov.filter(
                        estado_op__nombre__iexact=ESTADO_OP_COMPLETADA_LOWER
                    ).count()
                    count_cancelada = ops_de_la_ov.filter(
                        estado_op__nombre__iexact=ESTADO_OP_CANCELADA_LOWER
                    ).count()

                    if total_ops_en_ov > 0 and (
                        count_completada + count_cancelada == total_ops_en_ov
                    ):
                        if orden_venta_asociada.estado != "LISTA_ENTREGA":
                            estado_ov_anterior_str = (
                                orden_venta_asociada.get_estado_display()
                            )
                            orden_venta_asociada.estado = "LISTA_ENTREGA"
                            orden_venta_asociada.save(update_fields=["estado"])

                            descripcion_ov = f"Estado de la OV cambió de '{estado_ov_anterior_str}' a 'Lista para Entrega'."
                            HistorialOV.objects.create(
                                orden_venta=orden_venta_asociada,
                                descripcion=descripcion_ov,
                                tipo_evento="Cambio Estado OV",
                                realizado_por=request.user,
                            )

                            messages.info(
                                request,
                                f"Todos los ítems de la OV {orden_venta_asociada.numero_ov} están listos. El estado de la OV se ha actualizado a 'Lista para Entrega'.",
                            )
                            logger.info(
                                f"OV {orden_venta_asociada.numero_ov} actualizada a 'LISTA_ENTREGA' porque todas sus OPs han finalizado."
                            )
                except Exception as e:
                    logger.error(f"Error al actualizar estado de OV asociada a OP {op_actualizada.numero_op}: {e}")
                    messages.warning(
                        request,
                        "OP actualizada correctamente, pero hubo un problema al verificar el estado de la OV asociada.",
                    )

            return redirect(
                "App_LUMINOVA:produccion_detalle_op", op_id=op_actualizada.id
            )
        else:
            messages.error(
                request,
                "Error al actualizar la OP. Por favor, revise los datos del formulario.",
            )
            logger.warning(
                f"Formulario OrdenProduccionUpdateForm inválido para OP {op.id}: {form_update.errors.as_json()}"
            )
            if op.estado_op and op.estado_op.nombre.lower() in [
                ESTADO_OP_PAUSADA_LOWER,
                ESTADO_OP_CANCELADA_LOWER,
            ]:
                mostrar_boton_reportar = True
    else:
        form_update = OrdenProduccionUpdateForm(
            instance=op, estado_op_queryset=estado_op_queryset_para_form
        )
    estados_activos_para_reportar = [
        "insumos solicitados",
        "producción iniciada",
        "en proceso",
        "pausada",
        "producción con problemas",
    ]
    mostrar_boton_reportar = (
        op.estado_op and op.estado_op.nombre.lower() in estados_activos_para_reportar
    )

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
    # --- Lógica para resolver un reporte ---
    if resolver and reporte_id and request.method == "POST":
        reporte_a_resolver = get_object_or_404(Reportes, id=reporte_id)
        if not reporte_a_resolver.resuelto:
            reporte_a_resolver.resuelto = True
            reporte_a_resolver.fecha_resolucion = timezone.now()
            reporte_a_resolver.save()

            # Cambiar estado de la OP asociada, si la tiene
            op_asociada = reporte_a_resolver.orden_produccion_asociada
            if (
                op_asociada
                and op_asociada.estado_op
                and op_asociada.estado_op.nombre
                in ["Pausada", "Producción con Problemas"]
            ):
                try:
                    # Intenta volver al estado 'En Proceso' que es lo más lógico.
                    estado_reanudado = EstadoOrden.objects.get(
                        nombre__iexact="En Proceso"
                    )
                    op_asociada.estado_op = estado_reanudado
                    op_asociada.save()
                    messages.success(
                        request,
                        f"El problema del reporte {reporte_a_resolver.n_reporte} ha sido resuelto y la OP {op_asociada.numero_op} ha sido reanudada.",
                    )
                except EstadoOrden.DoesNotExist:
                    messages.warning(
                        request,
                        f"Reporte {reporte_a_resolver.n_reporte} resuelto, pero no se encontró el estado 'En Proceso' para reanudar la OP.",
                    )
            else:
                messages.success(
                    request,
                    f"El reporte {reporte_a_resolver.n_reporte} ha sido marcado como resuelto.",
                )
        else:
            messages.info(request, "Este reporte ya había sido resuelto anteriormente.")
        return redirect("App_LUMINOVA:reportes_produccion")

    # --- Lógica para mostrar las listas en pestañas (para peticiones GET) ---
    reportes_abiertos = (
        Reportes.objects.filter(resuelto=False)
        .select_related("orden_produccion_asociada", "reportado_por", "sector_reporta")
        .order_by("-fecha")
    )
    reportes_resueltos = (
        Reportes.objects.filter(resuelto=True)
        .select_related("orden_produccion_asociada", "reportado_por", "sector_reporta")
        .order_by("-fecha_resolucion")
    )

    # Detectar el parámetro de consulta 'tab'
    tab_activo = request.GET.get("tab", "abiertos")

    context = {
        "reportes_abiertos": reportes_abiertos,
        "reportes_resueltos": reportes_resueltos,
        "titulo_seccion": "Reportes de Producción",
        "tab_activo": tab_activo,
    }
    return render(request, "produccion/reportes.html", context)


@login_required
@transaction.atomic
def crear_reporte_produccion_view(request, op_id):
    orden_produccion = get_object_or_404(OrdenProduccion, id=op_id)

    # Solo permitir reportar si la OP está en un estado problemático o según tu lógica
    # if not (orden_produccion.estado_op and orden_produccion.estado_op.nombre.lower() in ["pausada", "cancelada", "producción con problemas"]):
    #     messages.error(request, "Solo se pueden crear reportes para Órdenes de Producción en estados problemáticos.")
    #     return redirect('App_LUMINOVA:produccion_detalle_op', op_id=op_id)

    if request.method == "POST":
        form = ReporteProduccionForm(request.POST, orden_produccion=orden_produccion)
        if form.is_valid():
            reporte = form.save(commit=False)
            reporte.orden_produccion_asociada = orden_produccion
            reporte.reportado_por = request.user
            reporte.fecha = timezone.now()

            # Generar n_reporte único
            reporte.n_reporte = generar_siguiente_numero_documento(Reportes, 'RP', 'n_reporte')

            reporte.save()  
            messages.success(
                request,
                f"Reporte '{reporte.n_reporte}' creado exitosamente para la OP {orden_produccion.numero_op}.",
            )
            return redirect(
                "App_LUMINOVA:reportes_produccion"
            )  # Ir a la lista de todos los reportes
        else:
            messages.error(
                request, "Por favor, corrija los errores en el formulario de reporte."
            )
    else:  # GET
        # Pasar la OP al form para preseleccionar el sector si es posible
        form = ReporteProduccionForm(orden_produccion=orden_produccion)

    context = {
        "form_reporte": form,
        "orden_produccion": orden_produccion,
        "titulo_seccion": f"Crear Reporte para OP: {orden_produccion.numero_op}",
    }
    return render(request, "produccion/crear_reporte.html", context)

