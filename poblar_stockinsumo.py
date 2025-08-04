#!/usr/bin/env python
"""
Script para poblar StockInsumo con los insumos actualizados
"""

from App_LUMINOVA.models import Insumo, Deposito, StockInsumo
from django.db import transaction

print("=== POBLANDO STOCKINSUMO ===")

# Limpiar registros existentes de StockInsumo
print("Limpiando registros existentes de StockInsumo...")
StockInsumo.objects.all().delete()

with transaction.atomic():
    count_created = 0
    for insumo in Insumo.objects.all():
        if insumo.deposito:
            stock_obj = StockInsumo.objects.create(
                insumo=insumo,
                cantidad=insumo.cantidad,
                deposito=insumo.deposito
            )
            count_created += 1
            print(f"Stock creado para insumo: {insumo.nombre}, Cantidad: {insumo.cantidad}, Depósito: {insumo.deposito.nombre}")
        else:
            print(f"Insumo {insumo.nombre} no tiene un depósito asignado. No se creó stock.")

print(f"\nTotal de registros creados en StockInsumo: {count_created}")

# Verificar por depósito
print(f"\n=== VERIFICACIÓN STOCKINSUMO POR DEPÓSITO ===")
for deposito in Deposito.objects.all():
    stocks = StockInsumo.objects.filter(deposito=deposito)
    bajo_stock = stocks.filter(cantidad__lt=15000)
    
    print(f"\n{deposito.nombre}:")
    print(f"  - Registros StockInsumo: {stocks.count()}")
    print(f"  - Con stock bajo: {bajo_stock.count()}")
    
    for stock in bajo_stock:
        print(f"    · {stock.insumo.descripcion[:40]}... Stock: {stock.cantidad}")

print(f"\n✅ StockInsumo poblado correctamente.")
