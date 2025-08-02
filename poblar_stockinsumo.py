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
                deposito=insumo.deposito,
                cantidad=insumo.stock or 0
            )
            print(f"Creado: {insumo.descripcion[:50]}... en {insumo.deposito.nombre} - Stock: {insumo.stock}")
            count_created += 1
        else:
            print(f"ADVERTENCIA: {insumo.descripcion} no tiene depósito asignado")

print(f"\nTotal registros StockInsumo creados: {count_created}")

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
