
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from datetime import timedelta
from core.common.utils import generar_siguiente_numero_documento
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import Insumo, Orden, Proveedor, OfertaProveedor, CategoriaInsumo
from .forms import OrdenCompraForm
import logging
logger = logging.getLogger(__name__)

@login_required
def compras_lista_oc_view(request):
    ordenes_compra = (
        Orden.objects.filter(tipo="compra")
        .select_related("proveedor", "insumo_principal")
        .order_by("-fecha_creacion")
    )
    context = {
        "ordenes_list": ordenes_compra,
        "titulo_seccion": "Listado de Órdenes de Compra",
    }
    return render(request, "compras/compras_lista_oc.html", context)

@login_required
def compras_desglose_view(request):
    UMBRAL_STOCK_BAJO_INSUMOS = 15000
    ESTADOS_OC_POST_BORRADOR = ["APROBADA", "ENVIADA_PROVEEDOR", "EN_TRANSITO", "RECIBIDA_PARCIAL", "RECIBIDA_TOTAL", "COMPLETADA"]
    insumos_ya_gestionados_ids = (
        Orden.objects.filter(tipo="compra", estado__in=ESTADOS_OC_POST_BORRADOR, insumo_principal__isnull=False)
        .values_list("insumo_principal_id", flat=True)
        .distinct()
    )
    insumos_criticos_para_gestionar = (
        Insumo.objects.filter(cantidad__lt=UMBRAL_STOCK_BAJO_INSUMOS)
        .exclude(id__in=insumos_ya_gestionados_ids)
        .select_related("categoria")
        .order_by("categoria__nombre", "cantidad", "descripcion")
    )
    context = {
        "insumos_criticos_list_con_estado": insumos_criticos_para_gestionar,
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO_INSUMOS,
        "titulo_seccion": "Gestionar Compra por Stock Bajo",
    }
    return render(request, "compras/compras_desglose.html", context)

@login_required
def compras_seguimiento_view(request):
    estados_en_seguimiento = ["ENVIADA_PROVEEDOR", "EN_TRANSITO", "RECIBIDA_PARCIAL"]
    ordenes = (
        Orden.objects.filter(tipo="compra", estado__in=estados_en_seguimiento)
        .select_related("proveedor")
        .order_by("-fecha_creacion")
    )
    context = {
        "ordenes_en_seguimiento": ordenes,
        "titulo_seccion": "Seguimiento de Órdenes de Compra",
    }
    return render(request, "compras/seguimiento.html", context)

@login_required
def compras_tracking_pedido_view(request, oc_id):
    orden_compra = get_object_or_404(Orden.objects.select_related("proveedor"), id=oc_id, tipo="compra")
    context = {"orden_compra": orden_compra}
    return render(request, "compras/compras_tracking_pedido.html", context)

@login_required
def compras_desglose_detalle_oc_view(request, numero_orden_desglose):
    context = {
        "numero_orden_desglose": numero_orden_desglose,
        "titulo_seccion": f"Detalle Desglose OC: {numero_orden_desglose}",
    }
    return render(request, "compras/compras_desglose_detalle.html", context)

@login_required
def compras_seleccionar_proveedor_para_insumo_view(request, insumo_id):
    insumo_objetivo = get_object_or_404(Insumo.objects.select_related("categoria"), id=insumo_id)
    if request.method == "POST":
        oferta_id_seleccionada = request.POST.get("oferta_proveedor_id")
        proveedor_fallback_id_seleccionado = request.POST.get("proveedor_fallback_id")
        proveedor_id_final_para_oc = None
        if oferta_id_seleccionada:
            try:
                oferta = OfertaProveedor.objects.get(id=oferta_id_seleccionada, insumo_id=insumo_id)
                proveedor_id_final_para_oc = oferta.proveedor.id
            except OfertaProveedor.DoesNotExist:
                messages.error(request, "La oferta seleccionada no es válida o no corresponde al insumo.")
                return redirect("insumos:compras_seleccionar_proveedor_para_insumo", insumo_id=insumo_id)
        elif proveedor_fallback_id_seleccionado:
            proveedor_id_final_para_oc = proveedor_fallback_id_seleccionado
        else:
            messages.error(request, "Debe seleccionar un proveedor u oferta.")
            return redirect("insumos:compras_seleccionar_proveedor_para_insumo", insumo_id=insumo_id)
        return redirect("insumos:compras_crear_oc_view", insumo_id=insumo_id, proveedor_id=proveedor_id_final_para_oc)
    ofertas = OfertaProveedor.objects.filter(insumo_id=insumo_id).select_related("proveedor").order_by("precio_unitario_compra", "tiempo_entrega_estimado_dias")
    proveedores_fallback = []
    if not ofertas.exists():
        proveedores_fallback = Proveedor.objects.all().order_by("nombre")[:5]
    UMBRAL_STOCK_BAJO_INSUMOS = 15000
    context = {
        "insumo_objetivo": insumo_objetivo,
        "ofertas_proveedores": ofertas,
        "proveedores_fallback": proveedores_fallback,
        "titulo_seccion": f"Seleccionar Oferta para: {insumo_objetivo.descripcion}",
        "umbral_stock_bajo": UMBRAL_STOCK_BAJO_INSUMOS,
    }
    return render(request, "compras/compras_seleccionar_proveedor.html", context)

@login_required
def compras_detalle_oc_view(request, oc_id):
    orden_compra = get_object_or_404(Orden.objects.select_related("proveedor", "insumo_principal__categoria"), id=oc_id, tipo="compra")
    context = {
        "oc": orden_compra,
        "titulo_seccion": f"Detalle OC: {orden_compra.numero_orden}",
    }
    return render(request, "compras/compras_detalle_oc.html", context)

@login_required
@transaction.atomic
def compras_crear_oc_view(request, insumo_id=None, proveedor_id=None):
    insumo_preseleccionado_obj = None
    proveedor_preseleccionado_obj = None
    initial_data = {}
    form_kwargs = {}
    if insumo_id:
        insumo_preseleccionado_obj = get_object_or_404(Insumo, id=insumo_id)
        initial_data['insumo_principal'] = insumo_preseleccionado_obj
        form_kwargs['insumo_fijado'] = insumo_preseleccionado_obj
        UMBRAL_STOCK_BAJO = 15000
        cantidad_sugerida = max(10, UMBRAL_STOCK_BAJO - insumo_preseleccionado_obj.stock)
        initial_data['cantidad_principal'] = cantidad_sugerida
        if proveedor_id:
            proveedor_preseleccionado_obj = get_object_or_404(Proveedor, id=proveedor_id)
            initial_data['proveedor'] = proveedor_preseleccionado_obj
            oferta_seleccionada = OfertaProveedor.objects.filter(insumo=insumo_preseleccionado_obj, proveedor=proveedor_preseleccionado_obj).first()
            if oferta_seleccionada:
                initial_data['precio_unitario_compra'] = oferta_seleccionada.precio_unitario_compra
                if oferta_seleccionada.tiempo_entrega_estimado_dias is not None:
                    try:
                        dias = int(oferta_seleccionada.tiempo_entrega_estimado_dias)
                        fecha_estimada = timezone.now().date() + timedelta(days=dias)
                        initial_data['fecha_estimada_entrega'] = fecha_estimada.strftime('%Y-%m-%d')
                    except (ValueError, TypeError): pass
    if request.method == 'POST':
        form = OrdenCompraForm(request.POST, **form_kwargs)
        if form.is_valid():
            orden_compra = form.save(commit=False)
            orden_compra.tipo = 'compra'
            orden_compra.estado = 'BORRADOR'
            orden_compra.numero_orden = generar_siguiente_numero_documento(Orden, 'OC', 'numero_orden')
            orden_compra.save()
            messages.success(request, f"Orden de Compra '{orden_compra.numero_orden}' creada en Borrador.")
            return redirect('insumos:compras_lista_oc_view')
        else:
            messages.error(request, "Por favor, corrija los errores del formulario.")
    else:
        form = OrdenCompraForm(initial=initial_data, **form_kwargs)
    context = {
        'form_oc': form,
        'titulo_seccion': 'Crear Orden de Compra',
        'insumo_preseleccionado': insumo_preseleccionado_obj,
    }
    return render(request, 'compras/compras_crear_editar_oc.html', context)
