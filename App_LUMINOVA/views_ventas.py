import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required

# Django Contrib Imports
from django.db import IntegrityError as DjangoIntegrityError
from django.db import transaction
from django.db.models import Prefetch, Q

# Django Core Imports
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

# Local Application Imports (Forms)
from .forms import (
    ClienteForm,
    FacturaForm,
    ItemOrdenVentaFormSet,
    ItemOrdenVentaFormSetCreacion,
    OrdenVentaForm,
)

# Local Application Imports (Models)
from .models import (
    Cliente,
    EstadoOrden,
    Factura,
    ItemOrdenVenta,
    OrdenProduccion,
    OrdenVenta,
    Reportes,
)
from .signals import get_client_ip

from .services.document_services import generar_siguiente_numero_documento
from .services.pdf_services import generar_pdf_factura
from .utils import es_admin, es_admin_o_rol

logger = logging.getLogger(__name__)

# --- VENTAS VIEWS ---
@login_required
def lista_clientes_view(request):
    if not es_admin_o_rol(request.user, ["ventas", "administrador"]):
        messages.error(request, "Acceso denegado.")
        return redirect("App_LUMINOVA:dashboard")

    clientes = Cliente.objects.all().order_by("nombre")
    form_para_crear = ClienteForm()  # Instancia para el modal de creación

    context = {
        "clientes_list": clientes,
        "cliente_form_crear": form_para_crear,  # Para el modal de creación
        "ClienteFormClass": ClienteForm,  # Pasamos la clase del formulario
        "titulo_seccion": "Gestión de Clientes",
    }
    return render(request, "ventas/ventas_clientes.html", context)


@login_required
@transaction.atomic
def crear_cliente_view(request):
    if not es_admin_o_rol(request.user, ["ventas", "administrador"]):
        messages.error(request, "Acción no permitida.")
        return redirect("App_LUMINOVA:lista_clientes")

    if request.method == "POST":
        form = ClienteForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Cliente creado exitosamente.")
            except DjangoIntegrityError:
                messages.error(
                    request, "Error: Un cliente con ese nombre o email ya existe."
                )
            except Exception as e:
                messages.error(request, f"Error inesperado al crear cliente: {e}")
            return redirect("App_LUMINOVA:lista_clientes")
        else:
            # Re-render con errores (para modales puede ser complejo, simplificamos)
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request, f"{form.fields[field].label or field}: {error}"
                    )
            return redirect("App_LUMINOVA:lista_clientes")
    return redirect("App_LUMINOVA:lista_clientes")


# ... (editar_cliente_view y eliminar_cliente_view pueden permanecer similares a como estaban) ...
@login_required
@transaction.atomic
def editar_cliente_view(request, cliente_id):
    if not es_admin_o_rol(request.user, ["ventas", "administrador"]):
        messages.error(request, "Acción no permitida.")
        return redirect("App_LUMINOVA:lista_clientes")
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == "POST":
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Cliente actualizado exitosamente.")
            except DjangoIntegrityError:
                messages.error(
                    request, "Error: Otro cliente ya tiene ese nombre o email."
                )
            except Exception as e:
                messages.error(request, f"Error inesperado al actualizar cliente: {e}")
            return redirect("App_LUMINOVA:lista_clientes")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(
                        request, f"{form.fields[field].label or field}: {error}"
                    )
            return redirect("App_LUMINOVA:lista_clientes")
    return redirect("App_LUMINOVA:lista_clientes")


@login_required
@transaction.atomic
def eliminar_cliente_view(request, cliente_id):
    if not es_admin_o_rol(request.user, ["ventas", "administrador"]):
        messages.error(request, "Acción no permitida.")
        return redirect("App_LUMINOVA:lista_clientes")
    cliente = get_object_or_404(Cliente, id=cliente_id)
    if request.method == "POST":
        try:
            nombre_cliente = cliente.nombre
            cliente.delete()
            messages.success(
                request, f'Cliente "{nombre_cliente}" eliminado exitosamente.'
            )
        except Exception as e:
            messages.error(
                request,
                f"Error al eliminar cliente: {e}. Verifique que no tenga órdenes asociadas.",
            )
    return redirect("App_LUMINOVA:lista_clientes")


@login_required
def ventas_lista_ov_view(request):
    from collections import OrderedDict
    ESTADOS_OV = OrderedDict([
        ("PENDIENTE", "Pendiente Confirmación"),
        ("CONFIRMADA", "Confirmada (Esperando Producción)"),
        ("INSUMOS_SOLICITADOS", "Insumos Solicitados"),
        ("PRODUCCION_INICIADA", "Producción Iniciada"),
        ("PRODUCCION_CON_PROBLEMAS", "Producción con Problemas"),
        ("LISTA_ENTREGA", "Lista para Entrega"),
        ("COMPLETADA", "Completada/Entregada"),
        ("CANCELADA", "Cancelada"),
    ])
    ordenes_de_venta_query = (
        OrdenVenta.objects.select_related("cliente")
        .prefetch_related(
            "items_ov__producto_terminado",
            Prefetch(
                "ops_generadas",
                queryset=OrdenProduccion.objects.select_related(
                    "estado_op", "producto_a_producir"
                )
                .prefetch_related(
                    Prefetch(
                        "reportes_incidencia",
                        queryset=Reportes.objects.select_related(
                            "reportado_por", "sector_reporta"
                        ).order_by("-fecha"),
                    )
                )
                .order_by("numero_op"),
                to_attr="lista_ops_con_reportes_y_estado",
            ),
        )
        .order_by("-fecha_creacion")
    )

    # Actualizar estados de OV basado en sus OPs asociadas usando el método centralizado
    for ov in ordenes_de_venta_query:
        ov.actualizar_estado_por_ops()

    ordenes_por_estado = {estado: [] for estado in ESTADOS_OV.keys()}
    for ov in ordenes_de_venta_query:
        ov.tiene_algun_reporte_asociado = False
        if hasattr(ov, "lista_ops_con_reportes_y_estado"):
            for op in ov.lista_ops_con_reportes_y_estado:
                if op.reportes_incidencia.all().exists():
                    ov.tiene_algun_reporte_asociado = True
                    break
        if ov.estado in ordenes_por_estado:
            ordenes_por_estado[ov.estado].append(ov)
    estados_ov_tabs = []
    for estado, nombre in ESTADOS_OV.items():
        ovs = ordenes_por_estado.get(estado, [])
        estados_ov_tabs.append((estado, nombre, ovs))
    context = {
        "estados_ov_tabs": estados_ov_tabs,
        "titulo_seccion": "Órdenes de Venta",
    }
    return render(request, "ventas/ventas_lista_ov.html", context)


@login_required
def ventas_crear_ov_view(request):
    """
    Gestiona la creación de una nueva Orden de Venta y sus ítems asociados.
    Al crearse exitosamente, también genera las Órdenes de Producción correspondientes.
    """
    if not es_admin_o_rol(request.user, ["ventas", "administrador"]):
        messages.error(request, "Acción no permitida.")
        return redirect("App_LUMINOVA:ventas_lista_ov")

    if request.method == "POST":
        form_ov = OrdenVentaForm(request.POST, prefix="ov")
        formset_items = ItemOrdenVentaFormSetCreacion(request.POST, prefix="items")

        if form_ov.is_valid() and formset_items.is_valid():
            try:
                with transaction.atomic():
                    ov_instance = form_ov.save(commit=False)
                    ov_instance.estado = "PENDIENTE"
                    ov_instance.save() # Se necesita ID para la relación

                    items_a_procesar = []
                    total_ov = 0
                    for form in formset_items:
                        if form.is_valid() and form.cleaned_data and not form.cleaned_data.get('DELETE'):
                            item = form.save(commit=False)
                            item.orden_venta = ov_instance
                            item.subtotal = item.cantidad * item.producto_terminado.precio_unitario
                            total_ov += item.subtotal
                            items_a_procesar.append(item)

                    if not items_a_procesar:
                        raise ValueError("Se debe añadir al menos un producto a la orden.")

                    ItemOrdenVenta.objects.bulk_create(items_a_procesar)
                    ov_instance.total_ov = total_ov
                    ov_instance.save(update_fields=['total_ov'])

                    estado_op_inicial = EstadoOrden.objects.get(nombre__iexact="Pendiente")

                    # Obtener el último número OP existente y generar secuencialmente en memoria
                    from django.db.models import Max
                    ultimo_numero_op = (
                        OrdenProduccion.objects.filter(numero_op__startswith='OP-')
                        .aggregate(max_num=Max('numero_op'))['max_num']
                    )
                    if ultimo_numero_op:
                        try:
                            ultimo_num = int(ultimo_numero_op.split('-')[1])
                        except Exception:
                            ultimo_num = 0
                    else:
                        ultimo_num = 0
                    ops_a_crear = []
                    for i, item_procesado in enumerate(items_a_procesar, start=1):
                        next_op_number = f"OP-{ultimo_num + i:05d}"
                        ops_a_crear.append(
                            OrdenProduccion(
                                numero_op=next_op_number,
                                orden_venta_origen=ov_instance,
                                producto_a_producir=item_procesado.producto_terminado,
                                cantidad_a_producir=item_procesado.cantidad,
                                estado_op=estado_op_inicial,
                            )
                        )
                    OrdenProduccion.objects.bulk_create(ops_a_crear)

                messages.success(request, f'Orden de Venta "{ov_instance.numero_ov}" y sus OPs asociadas se crearon exitosamente.')
                return redirect('App_LUMINOVA:ventas_detalle_ov', ov_id=ov_instance.id)

            except EstadoOrden.DoesNotExist:
                messages.error(request, "Error de configuración: El estado 'Pendiente' para OP no existe. No se pudo continuar.")
            except ValueError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f"Ocurrió un error inesperado. Por favor, intente de nuevo. Detalle: {e}")
                logger.exception("Error grave en la creación de OV/OPs")
    else: # GET
        initial_data = {'numero_ov': generar_siguiente_numero_documento(OrdenVenta, 'OV', 'numero_ov')}
        form_ov = OrdenVentaForm(prefix="ov", initial=initial_data)
        formset_items = ItemOrdenVentaFormSetCreacion(prefix="items", queryset=ItemOrdenVenta.objects.none())

    context = {
        'form_ov': form_ov,
        'formset_items': formset_items,
        'titulo_seccion': "Nueva Orden de Venta"
    }
    return render(request, "ventas/ventas_crear_ov.html", context)


@login_required
def ventas_detalle_ov_view(request, ov_id):
    orden_venta = get_object_or_404(
        OrdenVenta.objects.select_related("cliente").prefetch_related(
            "items_ov__producto_terminado",
            "ops_generadas__estado_op",  # Necesitamos el estado de cada OP
            "factura_asociada",
        ),
        id=ov_id,
    )

    factura_form = None
    puede_facturar = False
    detalle_cancelacion_factura = ""

    if not hasattr(orden_venta, "factura_asociada") or not orden_venta.factura_asociada:
        # Lógica para determinar si se puede facturar
        ops_asociadas = orden_venta.ops_generadas.all()
        if not ops_asociadas.exists() and orden_venta.estado == "CONFIRMADA":
            # Si no hay OPs (ej. productos solo de stock) y está confirmada, podría facturarse.
            # Esto depende de tu flujo si una OV puede no generar OPs.
            # Por ahora, asumimos que OVs CONFIRMADAS sin OPs son para productos ya en stock.
            puede_facturar = True  # O cambiar estado a LISTA_ENTREGA primero
        elif ops_asociadas.exists():
            ops_completadas = ops_asociadas.filter(
                estado_op__nombre__iexact="Completada"
            ).count()
            ops_canceladas = ops_asociadas.filter(
                estado_op__nombre__iexact="Cancelada"
            ).count()
            ops_totales = ops_asociadas.count()

            # Se puede facturar si todas las OPs no canceladas están completadas
            if ops_completadas + ops_canceladas == ops_totales and ops_completadas > 0:
                puede_facturar = True
                if ops_canceladas > 0:
                    detalle_cancelacion_factura = f"Nota: {ops_canceladas} orden(es) de producción asociada(s) fueron canceladas."
            elif (
                orden_venta.estado == "PRODUCCION_CON_PROBLEMAS"
                and ops_completadas > 0
                and (ops_completadas + ops_canceladas == ops_totales)
            ):
                # Caso específico donde la OV está con problemas pero hay partes completadas
                puede_facturar = True
                detalle_cancelacion_factura = f"Facturación parcial. Nota: {ops_canceladas} orden(es) de producción asociada(s) fueron canceladas."
            elif orden_venta.estado == "LISTA_ENTREGA":  # Ya está explícitamente lista
                puede_facturar = True

        if puede_facturar:
            factura_form = FacturaForm()
            # Si hay detalle de cancelación, podrías pasarlo al form o al contexto
            # para incluirlo en notas de la factura si el form lo permite.
            # form.fields['notas_factura'].initial = detalle_cancelacion_factura (si tuvieras ese campo)

    context = {
        "ov": orden_venta,
        "items_ov": orden_venta.items_ov.all(),
        "factura_form": factura_form,
        "puede_facturar": puede_facturar,  # Para la plantilla
        "detalle_cancelacion_factura": detalle_cancelacion_factura,  # Para la plantilla
        "titulo_seccion": f"Detalle Orden de Venta: {orden_venta.numero_ov}",
    }
    return render(request, "ventas/ventas_detalle_ov.html", context)


@login_required
@transaction.atomic
def ventas_generar_factura_view(request, ov_id):
    """
    Gestiona la creación de una factura para una Orden de Venta.
    Esta vista ahora solo genera la factura sin cambiar el estado final de la OV.
    El estado final a 'COMPLETADA' se gestiona desde el envío en depósito.
    """
    orden_venta = get_object_or_404(
        OrdenVenta.objects.prefetch_related(
            "items_ov__producto_terminado", "ops_generadas__estado_op"
        ),
        id=ov_id,
    )

    # 1. Verificar si ya existe una factura
    if hasattr(orden_venta, "factura_asociada") and orden_venta.factura_asociada:
        messages.warning(
            request,
            f"La factura para la OV {orden_venta.numero_ov} ya ha sido generada.",
        )
        return redirect("App_LUMINOVA:ventas_detalle_ov", ov_id=orden_venta.id)

    # 2. Verificar si la OV está en un estado que permite facturación
    #    La condición principal es que esté 'LISTA_ENTREGA'.
    puede_facturar_ahora = False
    if orden_venta.estado == "LISTA_ENTREGA":
        puede_facturar_ahora = True
    else:
        # Lógica de respaldo para casos donde el estado no se actualizó, pero las condiciones se cumplen.
        ops_asociadas = orden_venta.ops_generadas.all()
        if (
            not ops_asociadas.exists() and orden_venta.estado == "CONFIRMADA"
        ):  # OV de solo stock
            puede_facturar_ahora = True
        elif ops_asociadas.exists():
            ops_completadas_count = ops_asociadas.filter(
                estado_op__nombre__iexact="Completada"
            ).count()
            ops_canceladas_count = ops_asociadas.filter(
                estado_op__nombre__iexact="Cancelada"
            ).count()
            if ops_completadas_count > 0 and (
                ops_completadas_count + ops_canceladas_count == ops_asociadas.count()
            ):
                puede_facturar_ahora = (
                    True  # Todas las OPs están resueltas (completadas o canceladas)
                )

    if not puede_facturar_ahora:
        messages.error(
            request,
            f"La Orden de Venta {orden_venta.numero_ov} no está lista para ser facturada. Estado actual: '{orden_venta.get_estado_display()}'.",
        )
        return redirect("App_LUMINOVA:ventas_detalle_ov", ov_id=orden_venta.id)

    # 3. Procesar el formulario si es un método POST
    if request.method == "POST":
        form = FacturaForm(request.POST)
        if form.is_valid():
            try:
                factura = form.save(commit=False)
                factura.orden_venta = orden_venta
                # El total a facturar es el total de la OV, ya que solo se factura cuando todo está listo.
                factura.total_facturado = orden_venta.total_ov
                factura.fecha_emision = timezone.now()
                # El cliente se puede obtener de la OV, pero no es necesario guardarlo en la factura si no está en el modelo.
                # factura.cliente = orden_venta.cliente
                factura.save()

                # --- REGISTRO EN HISTORIAL ---
                from .models import (
                    HistorialOV,
                )  # Importación local para evitar importación circular

                HistorialOV.objects.create(
                    orden_venta=orden_venta,
                    descripcion=f"Se generó la factura N° {factura.numero_factura} por un total de ${factura.total_facturado:.2f}.",
                    tipo_evento="Facturado",
                    realizado_por=request.user,
                )

                # --- CORRECCIÓN CLAVE ---
                # YA NO CAMBIAMOS EL ESTADO DE LA OV A 'COMPLETADA' AQUÍ.
                # La OV permanece en 'LISTA_ENTREGA' hasta que se confirme el envío desde depósito.

                messages.success(
                    request,
                    f"Factura N° {factura.numero_factura} generada exitosamente para la OV {orden_venta.numero_ov}.",
                )
                return redirect("App_LUMINOVA:ventas_detalle_ov", ov_id=orden_venta.id)

            except DjangoIntegrityError:
                messages.error(
                    request,
                    f"Error: El número de factura '{form.cleaned_data.get('numero_factura')}' ya existe.",
                )
            except Exception as e:
                messages.error(
                    request, f"Ocurrió un error inesperado al generar la factura: {e}"
                )
                logger.exception(f"Error generando factura para OV {ov_id}")
        else:
            messages.error(
                request,
                "El formulario de la factura contiene errores. Por favor, inténtelo de nuevo.",
            )

    # Si la petición es GET o el formulario es inválido, redirigir de vuelta a la página de detalle.
    return redirect("App_LUMINOVA:ventas_detalle_ov", ov_id=orden_venta.id)


@login_required
@transaction.atomic
def ventas_editar_ov_view(request, ov_id):
    orden_venta = get_object_or_404(
        OrdenVenta.objects.prefetch_related(
            "ops_generadas__estado_op", "items_ov__producto_terminado"
        ),
        id=ov_id,
    )
    logger.info(
        f"Editando OV: {orden_venta.numero_ov}, Estado actual OV: {orden_venta.get_estado_display()}"
    )

    puede_editar_items_y_ops = True

    if orden_venta.estado in ["COMPLETADA", "CANCELADA"]:
        messages.warning(
            request,
            f"La Orden de Venta {orden_venta.numero_ov} está en estado '{orden_venta.get_estado_display()}' y no puede ser modificada.",
        )
        return redirect("App_LUMINOVA:ventas_detalle_ov", ov_id=orden_venta.id)

    if orden_venta.estado not in ["PENDIENTE", "CONFIRMADA"]:
        puede_editar_items_y_ops = False
        logger.info(
            f"Edición de ítems deshabilitada para OV {orden_venta.numero_ov} porque su estado es '{orden_venta.get_estado_display()}'."
        )

    if puede_editar_items_y_ops:
        estados_op_avanzados = [
            "insumos recibidos",
            "producción iniciada",
            "en proceso",
            "completada",
            "cancelada por producción",
        ]
        for op_asociada in orden_venta.ops_generadas.all():
            if (
                op_asociada.estado_op
                and op_asociada.estado_op.nombre.lower() in estados_op_avanzados
            ):
                puede_editar_items_y_ops = False
                messages.error(
                    request,
                    f"No se pueden modificar los ítems de la OV {orden_venta.numero_ov} porque la OP '{op_asociada.numero_op}' ya ha avanzado (Estado OP: {op_asociada.get_estado_op_display()}).",
                )
                break

    if request.method == "POST":
        form_ov = OrdenVentaForm(request.POST, instance=orden_venta, prefix="ov")

        if form_ov.is_valid():
            if puede_editar_items_y_ops:
                formset_items = ItemOrdenVentaFormSet(
                    request.POST, instance=orden_venta, prefix="items"
                )
                if formset_items.is_valid():
                    try:
                        ov_actualizada = form_ov.save(commit=False)

                        ops_a_revisar_o_eliminar = orden_venta.ops_generadas.filter(
                            Q(estado_op__nombre__iexact="Pendiente")
                            | Q(estado_op__nombre__iexact="Insumos Solicitados")
                        )
                        if ops_a_revisar_o_eliminar.exists():
                            logger.info(
                                f"Eliminando {ops_a_revisar_o_eliminar.count()} OPs en estado inicial para OV {ov_actualizada.numero_ov}."
                            )
                            ops_a_revisar_o_eliminar.delete()
                            messages.warning(
                                request,
                                "Órdenes de Producción asociadas (en estado inicial) han sido eliminadas y se regenerarán según los nuevos ítems.",
                            )

                        formset_items.save()
                        ov_actualizada.actualizar_total()
                        ov_actualizada.save()

                        estado_op_inicial = EstadoOrden.objects.filter(
                            nombre__iexact="Pendiente"
                        ).first()
                        if not estado_op_inicial:
                            messages.error(
                                request,
                                "Error crítico: Estado 'Pendiente' para OP no configurado. No se pudieron regenerar OPs.",
                            )
                        else:
                            # --- INICIO DE LA CORRECCIÓN ---
                            for item_guardado in ov_actualizada.items_ov.all():
                                # Lógica correcta para generar número de OP secuencial
                                next_op_number = generar_siguiente_numero_documento(OrdenProduccion, 'OP', 'numero_op')

                                OrdenProduccion.objects.create(
                                    numero_op=next_op_number,
                                    orden_venta_origen=ov_actualizada,
                                    producto_a_producir=item_guardado.producto_terminado,
                                    cantidad_a_producir=item_guardado.cantidad,
                                    estado_op=estado_op_inicial,
                                )
                                messages.info(
                                    request,
                                    f'Nueva OP "{next_op_number}" generada para "{item_guardado.producto_terminado.descripcion}".',
                                )
                            # --- FIN DE LA CORRECCIÓN ---

                        messages.success(
                            request,
                            f"Orden de Venta '{ov_actualizada.numero_ov}' actualizada exitosamente.",
                        )
                        return redirect(
                            "App_LUMINOVA:ventas_detalle_ov", ov_id=ov_actualizada.id
                        )

                    except Exception as e:
                        messages.error(request, f"Error inesperado al guardar: {e}")
                        logger.exception(f"Error al editar y guardar OV {ov_id}:")
                else:
                    messages.error(
                        request,
                        "Por favor, corrija los errores en los ítems de la orden.",
                    )
            else:
                try:
                    ov_actualizada = form_ov.save()
                    messages.success(
                        request,
                        f"Datos generales de la Orden de Venta '{ov_actualizada.numero_ov}' actualizados.",
                    )
                    return redirect(
                        "App_LUMINOVA:ventas_detalle_ov", ov_id=ov_actualizada.id
                    )
                except Exception as e:
                    messages.error(
                        request, f"Error al guardar los datos generales: {e}"
                    )
        else:
            messages.error(
                request,
                "Por favor, corrija los errores en los datos generales de la orden.",
            )
            if puede_editar_items_y_ops:
                formset_items = ItemOrdenVentaFormSet(
                    request.POST, instance=orden_venta, prefix="items"
                )
            else:
                formset_items = ItemOrdenVentaFormSet(
                    instance=orden_venta, prefix="items"
                )

    else:  # GET request
        form_ov = OrdenVentaForm(instance=orden_venta, prefix="ov")
        formset_items = ItemOrdenVentaFormSet(instance=orden_venta, prefix="items")

    context = {
        "form_ov": form_ov,
        "formset_items": formset_items,
        "orden_venta": orden_venta,
        "titulo_seccion": f"Editar Orden de Venta: {orden_venta.numero_ov}",
        "puede_editar_items": puede_editar_items_y_ops,
    }
    return render(request, "ventas/ventas_editar_ov.html", context)


@login_required
@transaction.atomic
@require_POST  # Esta acción solo debe ser por POST desde el modal
def ventas_cancelar_ov_view(request, ov_id):
    # if not es_admin_o_rol(request.user, ['ventas', 'administrador']):
    #     messages.error(request, "Acción no permitida.")
    #     return redirect('App_LUMINOVA:ventas_lista_ov')

    orden_venta = get_object_or_404(OrdenVenta, id=ov_id)

    if orden_venta.estado in ["COMPLETADA", "CANCELADA"]:
        messages.warning(
            request,
            f"La Orden de Venta {orden_venta.numero_ov} ya está {orden_venta.get_estado_display()} y no puede cancelarse nuevamente.",
        )
        return redirect("App_LUMINOVA:ventas_detalle_ov", ov_id=ov_id)

    estado_op_cancelada = EstadoOrden.objects.filter(nombre__iexact="Cancelada").first()
    estado_op_completada = EstadoOrden.objects.filter(
        nombre__iexact="Completada"
    ).first()  # O 'Terminado'

    if not estado_op_cancelada:
        messages.error(
            request, "Error crítico: El estado 'Cancelada' para OP no está configurado."
        )
        return redirect("App_LUMINOVA:ventas_detalle_ov", ov_id=ov_id)

    ops_asociadas = orden_venta.ops_generadas.all()
    ops_canceladas_count = 0
    ops_ya_completadas = 0
    
    for op in ops_asociadas:
        if (
            op.estado_op != estado_op_completada
        ):  # No cancelar OPs que ya se completaron
            op.estado_op = estado_op_cancelada
            op.save(update_fields=["estado_op"])
            ops_canceladas_count += 1
            messages.info(
                request,
                f"Orden de Producción {op.numero_op} asociada ha sido cancelada.",
            )
        else:
            ops_ya_completadas += 1
            messages.warning(
                request,
                f"Orden de Producción {op.numero_op} ya está completada y no se cancelará.",
            )

    # Actualizar estado de la OV usando el método centralizado
    # En caso de cancelación manual, forzamos el estado a CANCELADA
    orden_venta.estado = "CANCELADA"
    orden_venta.save(update_fields=["estado"])
    
    # Registrar en historial
    try:
        from .models import HistorialOV
        HistorialOV.objects.create(
            orden_venta=orden_venta,
            descripcion=f"OV cancelada por {request.user.get_full_name() or request.user.username}. "
                        f"OPs canceladas: {ops_canceladas_count}, OPs completadas (no canceladas): {ops_ya_completadas}",
            tipo_evento="Cancelación",
            realizado_por=request.user,
        )
    except Exception as e:
        logger.warning(f"No se pudo registrar en historial la cancelación de OV {orden_venta.numero_ov}: {e}")
    
    messages.success(
        request, f"Orden de Venta {orden_venta.numero_ov} ha sido cancelada."
    )

    return redirect("App_LUMINOVA:ventas_lista_ov")

# --- PDF VIEW ---
@login_required
def ventas_ver_factura_pdf_view(request, factura_id):
    """
    Vista que obtiene los datos de una factura y delega la generación
    del PDF a un servicio dedicado.
    """
    try:
        # Esta consulta optimizada busca todo lo necesario de una vez
        factura = (
            Factura.objects.select_related(
                "orden_venta__cliente"
            )
            .prefetch_related(
                Prefetch(
                    "orden_venta__items_ov",
                    queryset=ItemOrdenVenta.objects.select_related("producto_terminado"),
                )
            )
            .get(id=factura_id)
        )
    except Factura.DoesNotExist:
        messages.error(request, "La factura solicitada no existe.")
        return redirect("App_LUMINOVA:ventas_lista_ov")

    # Llamamos a nuestro servicio y retornamos directamente su respuesta
    return generar_pdf_factura(factura)
