# Script: sincronizar_stock_unificado.py
from App_LUMINOVA.models import Insumo, ProductoTerminado, StockInsumo, StockProductoTerminado, Deposito
from django.db import transaction

print("=== SINCRONIZACIÓN DE STOCK UNIFICADO ===")

with transaction.atomic():
    # 1. Sincronizar Insumos
    for insumo in Insumo.objects.all():
        if insumo.deposito:
            stock_obj, created = StockInsumo.objects.get_or_create(
                insumo=insumo,
                deposito=insumo.deposito,
                defaults={'cantidad': insumo.stock or 0}
            )
            if not created and stock_obj.cantidad != insumo.stock:
                # Usar el valor más reciente
                stock_obj.cantidad = insumo.stock or 0
                stock_obj.save()
            print(f"✓ Insumo: {insumo.descripcion} - Stock: {stock_obj.cantidad}")
    
    # 2. Sincronizar Productos
    for producto in ProductoTerminado.objects.all():
        if producto.deposito:
            stock_obj, created = StockProductoTerminado.objects.get_or_create(
                producto=producto,
                deposito=producto.deposito,
                defaults={'cantidad': producto.stock or 0}
            )
            if not created and stock_obj.cantidad != producto.stock:
                stock_obj.cantidad = producto.stock or 0
                stock_obj.save()
            print(f"✓ Producto: {producto.descripcion} - Stock: {stock_obj.cantidad}")

print("Sincronización completada")