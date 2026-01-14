from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from .models import (
    MovimientoStock, Deposito, Insumo, ProductoTerminado, 
    CategoriaProductoTerminado, StockInsumo, StockProductoTerminado
)
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction  # Ensure this import is present
from .empresa_filters import get_depositos_empresa, filter_insumos_por_empresa, filter_productos_por_empresa

@login_required
def historial_transferencias_view(request):
    # FILTRO POR EMPRESA: Obtener solo depósitos, insumos y productos de la empresa
    depositos = get_depositos_empresa(request)
    usuarios = User.objects.all()
    insumos = filter_insumos_por_empresa(request)
    productos = filter_productos_por_empresa(request)
    
    # FILTRO POR EMPRESA: Solo transferencias entre depósitos de la empresa
    # Obtener todas las transferencias (insumos y productos) filtradas por empresa
    transferencias = MovimientoStock.objects.filter(
        tipo="transferencia",
        deposito_origen__in=depositos
    ).select_related(
        "insumo", "producto", "deposito_origen", "deposito_destino", "usuario"
    ).order_by("-fecha")

    # Filtros
    deposito_origen_id = request.GET.get("deposito_origen")
    deposito_destino_id = request.GET.get("deposito_destino")
    usuario_id = request.GET.get("usuario")
    insumo_id = request.GET.get("insumo")
    producto_id = request.GET.get("producto")
    tipo_item = request.GET.get("tipo_item")  # "insumo" o "producto"
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    if deposito_origen_id:
        transferencias = transferencias.filter(deposito_origen_id=deposito_origen_id)
    if deposito_destino_id:
        transferencias = transferencias.filter(deposito_destino_id=deposito_destino_id)
    if usuario_id:
        transferencias = transferencias.filter(usuario_id=usuario_id)
    if insumo_id:
        transferencias = transferencias.filter(insumo_id=insumo_id)
    if producto_id:
        transferencias = transferencias.filter(producto_id=producto_id)
    if tipo_item == "insumo":
        transferencias = transferencias.filter(insumo__isnull=False)
    elif tipo_item == "producto":
        transferencias = transferencias.filter(producto__isnull=False)
    if fecha_desde:
        transferencias = transferencias.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        transferencias = transferencias.filter(fecha__lte=fecha_hasta)

    if request.method == "POST":
        tipo_item = request.POST.get("tipo_item")  # "insumo" o "producto"
        item_id = request.POST.get("item_id")
        deposito_origen_id = request.POST.get("deposito_origen")
        deposito_destino_id = request.POST.get("deposito_destino")
        cantidad = int(request.POST.get("cantidad", 0))

        if item_id and deposito_origen_id and deposito_destino_id and cantidad > 0:
            deposito_origen = Deposito.objects.get(id=deposito_origen_id)
            deposito_destino = Deposito.objects.get(id=deposito_destino_id)

            with transaction.atomic():
                if tipo_item == "insumo":
                    insumo = Insumo.objects.get(id=item_id)
                    
                    # Obtener o crear registro de stock en origen
                    stock_origen, _ = StockInsumo.objects.get_or_create(
                        insumo=insumo,
                        deposito=deposito_origen,
                        defaults={'cantidad': 0, 'empresa': deposito_origen.empresa}
                    )

                    # Verificar stock suficiente en el depósito origen
                    if stock_origen.cantidad >= cantidad:
                        # Restar del origen
                        stock_origen.cantidad -= cantidad
                        stock_origen.save(update_fields=["cantidad"])

                        # Sumar al destino
                        stock_destino, _ = StockInsumo.objects.get_or_create(
                            insumo=insumo,
                            deposito=deposito_destino,
                            defaults={'cantidad': 0, 'empresa': deposito_destino.empresa}
                        )
                        stock_destino.cantidad += cantidad
                        stock_destino.save(update_fields=["cantidad"])
                    else:
                        raise ValueError("Stock insuficiente en el depósito origen para el insumo.")

                elif tipo_item == "producto":
                    producto = ProductoTerminado.objects.get(id=item_id)
                    
                    # Obtener o crear registro de stock en origen
                    stock_origen, _ = StockProductoTerminado.objects.get_or_create(
                        producto=producto,
                        deposito=deposito_origen,
                        defaults={'cantidad': 0, 'empresa': deposito_origen.empresa}
                    )

                    # Verificar stock suficiente en el depósito origen
                    if stock_origen.cantidad >= cantidad:
                        # Restar del origen
                        stock_origen.cantidad -= cantidad
                        stock_origen.save(update_fields=["cantidad"])

                        # Sumar al destino
                        stock_destino, _ = StockProductoTerminado.objects.get_or_create(
                            producto=producto,
                            deposito=deposito_destino,
                            defaults={'cantidad': 0, 'empresa': deposito_destino.empresa}
                        )
                        stock_destino.cantidad += cantidad
                        stock_destino.save(update_fields=["cantidad"])
                    else:
                        raise ValueError("Stock insuficiente en el depósito origen para el producto terminado.")

    context = {
        "transferencias": transferencias,
        "depositos": depositos,
        "usuarios": usuarios,
        "insumos": insumos,
        "productos": productos,
        "filtros": {
            "deposito_origen_id": deposito_origen_id,
            "deposito_destino_id": deposito_destino_id,
            "usuario_id": usuario_id,
            "insumo_id": insumo_id,
            "producto_id": producto_id,
            "tipo_item": tipo_item,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    }
    return render(request, "deposito/historial_transferencias.html", context)
