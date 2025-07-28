
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from .models import Deposito, StockProductoTerminado
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Deposito, StockProductoTerminado
from productos.models import ProductoTerminado, ComponenteProducto, EstadoOrden, OrdenProduccion, LoteProductoTerminado, CategoriaProductoTerminado
from insumos.models import Insumo, Orden, CategoriaInsumo
import logging
logger = logging.getLogger(__name__)

@login_required
def deposito_selector_view(request):
    depositos = Deposito.objects.all()
    if request.method == "GET" and "deposito_id" in request.GET:
        deposito_id = request.GET.get("deposito_id")
        if deposito_id:
            return redirect(f"/deposito/deposito/?deposito_id={deposito_id}")
    return render(request, "deposito/deposito_selector.html", {"depositos": depositos})

@login_required
@transaction.atomic
def deposito_enviar_insumos_op_view(request, op_id):
    op = get_object_or_404(OrdenProduccion.objects.select_related("orden_venta_origen", "producto_a_producir"), id=op_id)
    if request.method == "POST":
        if not op.estado_op or op.estado_op.nombre.lower() != "insumos solicitados":
            messages.error(request, f"La OP {op.numero_op} no está en estado 'Insumos Solicitados'. No se pueden enviar insumos.")
            return redirect("depositos:deposito_detalle_solicitud_op", op_id=op.id)
        insumos_descontados_correctamente = True
        errores_stock = []
        if not op.producto_a_producir:
            messages.error(request, f"Error crítico: La OP {op.numero_op} no tiene un producto asignado.")
            return redirect("depositos:deposito_detalle_solicitud_op", op_id=op.id)
        componentes_requeridos = ComponenteProducto.objects.filter(producto_terminado=op.producto_a_producir).select_related("insumo")
        if not componentes_requeridos.exists():
            messages.error(request, f"No se puede procesar: No hay BOM definido para el producto '{op.producto_a_producir.descripcion}'.")
            return redirect("depositos:deposito_detalle_solicitud_op", op_id=op.id)
        for comp in componentes_requeridos:
            cantidad_a_descontar = comp.cantidad_necesaria * op.cantidad_a_producir
            try:
                insumo_a_actualizar = Insumo.objects.get(id=comp.insumo.id)
                if insumo_a_actualizar.stock >= cantidad_a_descontar:
                    Insumo.objects.filter(id=insumo_a_actualizar.id).update(stock=F("stock") - cantidad_a_descontar)
                else:
                    errores_stock.append(f"Stock insuficiente para '{insumo_a_actualizar.descripcion}'. Requeridos: {cantidad_a_descontar}, Disponible: {insumo_a_actualizar.stock}")
                    insumos_descontados_correctamente = False
            except Insumo.DoesNotExist:
                errores_stock.append(f"Insumo '{comp.insumo.descripcion}' (ID: {comp.insumo.id}) no encontrado durante el descuento. Error de datos.")
                insumos_descontados_correctamente = False
                break
        if errores_stock:
            for error_msg in errores_stock:
                messages.error(request, error_msg)
        if insumos_descontados_correctamente:
            try:
                nombre_estado_op_post_deposito = "Insumos Recibidos"
                estado_siguiente_op_obj = EstadoOrden.objects.get(nombre__iexact=nombre_estado_op_post_deposito)
                op.estado_op = estado_siguiente_op_obj
                if not op.fecha_inicio_real:
                    op.fecha_inicio_real = timezone.now()
                op.save(update_fields=["estado_op", "fecha_inicio_real"])
                messages.success(request, f"Insumos para OP {op.numero_op} marcados como enviados/recibidos. OP ahora en estado '{estado_siguiente_op_obj.nombre}'.")
            except EstadoOrden.DoesNotExist:
                messages.error(request, f"Error de Configuración: El estado de OP '{nombre_estado_op_post_deposito}' no fue encontrado. Insumos descontados, pero el estado de la OP no se actualizó correctamente.")
            return redirect("depositos:deposito_solicitudes_insumos")
        else:
            return redirect("depositos:deposito_detalle_solicitud_op", op_id=op.id)
    messages.info(request, "Esta acción de enviar insumos debe realizarse mediante POST desde la página de detalle de la solicitud.")
    return redirect("depositos:deposito_detalle_solicitud_op", op_id=op.id)

@login_required
def deposito_solicitudes_insumos_view(request):
    ops_pendientes_preparacion = OrdenProduccion.objects.none()
    ops_con_insumos_enviados = OrdenProduccion.objects.none()
    try:
        estado_insumos_solicitados_obj = EstadoOrden.objects.filter(nombre__iexact="Insumos Solicitados").first()
        if estado_insumos_solicitados_obj:
            ops_pendientes_preparacion = (
                OrdenProduccion.objects.filter(estado_op=estado_insumos_solicitados_obj)
                .select_related("producto_a_producir", "estado_op", "orden_venta_origen__cliente")
                .order_by("fecha_solicitud")
            )
        estado_en_proceso_obj = EstadoOrden.objects.filter(nombre__iexact="En Proceso").first()
        if estado_en_proceso_obj:
            ops_con_insumos_enviados = (
                OrdenProduccion.objects.filter(estado_op=estado_en_proceso_obj)
                .select_related("producto_a_producir", "estado_op", "orden_venta_origen__cliente")
                .order_by("-fecha_inicio_real", "-fecha_solicitud")
            )
    except Exception as e:
        messages.error(request, f"Ocurrió un error inesperado al cargar las solicitudes de insumos: {e}")
    context = {
        "ops_pendientes_list": ops_pendientes_preparacion,
        "ops_enviadas_list": ops_con_insumos_enviados,
        "titulo_seccion": "Gestión de Insumos para Producción",
    }
    return render(request, "deposito/deposito_solicitudes_insumos.html", context)

@login_required
def deposito_view(request):
    depositos = Deposito.objects.all()
    deposito_id = request.GET.get("deposito_id")
    deposito_seleccionado = None
    if not deposito_id:
        return redirect('depositos:deposito_selector')
    if deposito_id:
        deposito_seleccionado = Deposito.objects.filter(id=deposito_id).first()
    if not deposito_seleccionado and depositos.exists():
        deposito_seleccionado = depositos.first()

    # Filtrar categorías de insumos y productos terminados SOLO por los que tienen stock en este depósito
    categorias_I = CategoriaInsumo.objects.filter(
        insumo__stockproductoterminado__deposito=deposito_seleccionado
    ).distinct()
    categorias_PT = CategoriaProductoTerminado.objects.filter(
        productos_terminados__stocks__deposito=deposito_seleccionado
    ).distinct()

    # Filtrar productos terminados y stock SOLO de este depósito
    productos_terminados = ProductoTerminado.objects.filter(
        stocks__deposito=deposito_seleccionado
    ).select_related("categoria").distinct()
    productos_stock_por_deposito = []
    for pt in productos_terminados:
        stock_en_deposito = pt.get_stock_en_deposito(deposito_seleccionado)
        productos_stock_por_deposito.append({"producto": pt, "stock": stock_en_deposito, "deposito": deposito_seleccionado})

    # Filtrar OPs pendientes SOLO de este depósito (asumiendo que OrdenProduccion tiene un campo deposito)
    ops_pendientes_deposito_list = OrdenProduccion.objects.none()
    ops_pendientes_deposito_count = 0
    try:
        estado_sol = EstadoOrden.objects.filter(nombre__iexact="Insumos Solicitados").first()
        if estado_sol:
            ops_pendientes_deposito_list = (
                OrdenProduccion.objects.filter(estado_op=estado_sol, deposito=deposito_seleccionado)
                .select_related("producto_a_producir")
                .order_by("fecha_solicitud")
            )
            ops_pendientes_deposito_count = ops_pendientes_deposito_list.count()
    except Exception as e_op:
        logger.error(f"Deposito_view (OPs): Excepción al cargar OPs: {e_op}")

    # Filtrar lotes en stock SOLO de este depósito (asumiendo que LoteProductoTerminado tiene campo deposito o se puede inferir)
    lotes_en_stock = (
        LoteProductoTerminado.objects.filter(enviado=False, producto__stocks__deposito=deposito_seleccionado)
        .select_related("producto", "op_asociada")
        .order_by("-fecha_creacion")
        .distinct()
    )

    UMBRAL_STOCK_BAJO_INSUMOS = 15000
    # Filtrar insumos con stock bajo SOLO de este depósito (asumiendo que Insumo tiene stock por depósito, si no, ajustar modelo)
    insumos_con_stock_bajo = Insumo.objects.filter(
        stockproductoterminado__deposito=deposito_seleccionado,
        stockproductoterminado__cantidad__lt=UMBRAL_STOCK_BAJO_INSUMOS
    ).distinct()
    ESTADOS_OC_EN_PROCESO = ["APROBADA", "ENVIADA_PROVEEDOR", "EN_TRANSITO", "RECIBIDA_PARCIAL"]
    insumos_a_gestionar = []
    insumos_en_pedido = []
    for insumo in insumos_con_stock_bajo:
        oc_en_proceso = (
            Orden.objects.filter(insumo_principal=insumo, estado__in=ESTADOS_OC_EN_PROCESO)
            .order_by("-fecha_creacion")
            .first()
        )
        if oc_en_proceso:
            insumos_en_pedido.append({"insumo": insumo, "oc": oc_en_proceso})
        else:
            insumos_a_gestionar.append({"insumo": insumo})

    from App_LUMINOVA.forms import MovimientoStockProductoTerminadoForm
    if request.method == "POST":
        form = MovimientoStockProductoTerminadoForm(request.POST)
        if form.is_valid():
            producto = form.cleaned_data["producto"]
            deposito = form.cleaned_data["deposito"]
            cantidad = form.cleaned_data["cantidad"]
            tipo_movimiento = form.cleaned_data["tipo_movimiento"]
            if tipo_movimiento == "ingreso":
                producto.agregar_stock(cantidad, deposito)
                messages.success(request, f"Se ingresaron {cantidad} unidades de '{producto}' en '{deposito}'.")
            elif tipo_movimiento == "egreso":
                if producto.quitar_stock(cantidad, deposito):
                    messages.success(request, f"Se egresaron {cantidad} unidades de '{producto}' de '{deposito}'.")
                else:
                    messages.error(request, f"No hay suficiente stock de '{producto}' en '{deposito}' para egresar {cantidad} unidades.")
            return redirect(f"{request.path}?deposito_id={deposito.id}")
        else:
            messages.error(request, "Formulario inválido. Verifique los datos ingresados.")
        form_movimiento_stock = form
    else:
        form_movimiento_stock = MovimientoStockProductoTerminadoForm()

    context = {
        "categorias_I": categorias_I,
        "categorias_PT": categorias_PT,
        "depositos": depositos,
        "deposito_seleccionado": deposito_seleccionado,
        "productos_stock_por_deposito": productos_stock_por_deposito,
        "ops_pendientes_deposito_list": ops_pendientes_deposito_list,
        "ops_pendientes_deposito_count": ops_pendientes_deposito_count,
        "lotes_productos_terminados_en_stock": lotes_en_stock,
        "insumos_a_gestionar_list": insumos_a_gestionar,
        "insumos_en_pedido_list": insumos_en_pedido,
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO_INSUMOS,
        "form_movimiento_stock": form_movimiento_stock,
    }
    return render(request, "deposito/deposito.html", context)

@login_required
def recepcion_pedidos_view(request):
    ocs_en_transito = (
        Orden.objects.filter(tipo="compra", estado="EN_TRANSITO")
        .select_related("proveedor", "insumo_principal")
        .order_by("fecha_estimada_entrega")
    )
    context = {
        "ordenes_a_recibir": ocs_en_transito,
        "titulo_seccion": "Recepción de Pedidos de Compra",
    }
    return render(request, "deposito/deposito_recepcion.html", context)

@login_required
@require_POST
@transaction.atomic
def recibir_pedido_oc_view(request, oc_id):
    orden_a_recibir = get_object_or_404(Orden, id=oc_id, estado="EN_TRANSITO")
    insumo_recibido = orden_a_recibir.insumo_principal
    cantidad_recibida = orden_a_recibir.cantidad_principal
    if insumo_recibido and cantidad_recibida:
        insumo_recibido.stock = F("stock") + cantidad_recibida
        insumo_recibido.cantidad_en_pedido = F("cantidad_en_pedido") - cantidad_recibida
        insumo_recibido.save(update_fields=["stock", "cantidad_en_pedido"])
        orden_a_recibir.estado = "COMPLETADA"
        orden_a_recibir.save(update_fields=["estado"])
        messages.success(request, f"Pedido {orden_a_recibir.numero_orden} recibido exitosamente. Se agregaron {cantidad_recibida} unidades de '{insumo_recibido.descripcion}' al stock.")
    else:
        messages.error(request, f"Error: La OC {orden_a_recibir.numero_orden} no tiene un insumo o cantidad principal válidos.")
    return redirect("depositos:deposito_recepcion_pedidos")
from core.common.utils import es_admin


@login_required
def deposito_stock_view(request, deposito_id):
    deposito = get_object_or_404(Deposito, id=deposito_id)
    # Si no es admin, solo puede ver su propio depósito (asumiendo que el usuario tiene un campo deposito)
    if not es_admin(request.user):
        if hasattr(request.user, "deposito"):
            if request.user.deposito.id != deposito.id:
                return render(request, "403.html", {"mensaje": "No tienes permiso para ver este depósito."})
        else:
            return render(request, "403.html", {"mensaje": "No tienes depósito asignado."})
    stocks = StockProductoTerminado.objects.filter(deposito=deposito)
    return render(request, "depositos/stock_por_deposito.html", {"deposito": deposito, "stocks": stocks})
