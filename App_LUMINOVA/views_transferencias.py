from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from .models import MovimientoStock, Deposito, Insumo, ProductoTerminado, CategoriaProductoTerminado
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

                    # Verificar stock suficiente en el depósito origen
                    if insumo.stock >= cantidad:
                        insumo.stock -= cantidad
                        insumo.save(update_fields=["stock"])

                        # Actualizar o crear stock en el depósito destino
                        insumo_destino, created = Insumo.objects.get_or_create(
                            id=insumo.id, defaults={"stock": 0, "deposito": deposito_destino}
                        )
                        insumo_destino.stock += cantidad
                        insumo_destino.save(update_fields=["stock"])
                    else:
                        raise ValueError("Stock insuficiente en el depósito origen para el insumo.")

                elif tipo_item == "producto":
                    producto = ProductoTerminado.objects.get(id=item_id)

                    # Verificar stock suficiente en el depósito origen
                    if producto.stock >= cantidad:
                        producto.stock -= cantidad
                        producto.save(update_fields=["stock"])

                        # Actualizar o crear stock en el depósito destino
                        producto_destino, created = ProductoTerminado.objects.get_or_create(
                            id=producto.id, defaults={"stock": 0, "deposito": deposito_destino}
                        )
                        producto_destino.stock += cantidad
                        producto_destino.save(update_fields=["stock"])
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
