#!/usr/bin/env python
"""
Script para verificar y corregir problemas con depósitos e insumos
Ejecutar con: python manage.py shell < verificar_y_corregir_depositos.py
"""

from App_LUMINOVA.models import Insumo, Deposito, CategoriaInsumo, StockInsumo, ProductoTerminado, StockProductoTerminado
from django.db import transaction

print("=== VERIFICACIÓN Y CORRECCIÓN DE DEPÓSITOS E INSUMOS ===")

# 1. Verificar estado actual
print("\n1. ESTADO ACTUAL:")
total_insumos = Insumo.objects.count()
total_depositos = Deposito.objects.count()
insumos_sin_deposito = Insumo.objects.filter(deposito__isnull=True)

print(f"Total insumos: {total_insumos}")
print(f"Total depósitos: {total_depositos}")
print(f"Insumos SIN depósito: {insumos_sin_deposito.count()}")

# 2. Mostrar depósitos disponibles
print("\n2. DEPÓSITOS DISPONIBLES:")
for deposito in Deposito.objects.all():
    insumos_del_deposito = Insumo.objects.filter(deposito=deposito)
    print(f"- {deposito.nombre} (ID: {deposito.id}) - Insumos: {insumos_del_deposito.count()}")

# 3. Crear depósito por defecto si no existe
deposito_central, created = Deposito.objects.get_or_create(
    nombre="Depósito Central Luminova",
    defaults={
        'ubicacion': 'Central',
        'capacidad_maxima': 100000
    }
)

if created:
    print(f"\n3. CREADO DEPÓSITO: {deposito_central.nombre}")
else:
    print(f"\n3. DEPÓSITO EXISTENTE: {deposito_central.nombre}")

# 4. Asignar insumos sin depósito al depósito central
if insumos_sin_deposito.exists():
    print(f"\n4. ASIGNANDO {insumos_sin_deposito.count()} INSUMOS AL DEPÓSITO CENTRAL:")
    
    with transaction.atomic():
        count = 0
        for insumo in insumos_sin_deposito:
            # Asignar depósito
            insumo.deposito = deposito_central
            insumo.save(update_fields=['deposito'])
            count += 1
            print(f"  - {insumo.descripcion} -> {deposito_central.nombre}")
        
        print(f"Total insumos reasignados: {count}")

# 5. Verificar categorías sin depósito
categorias_sin_deposito = CategoriaInsumo.objects.filter(deposito__isnull=True)
if categorias_sin_deposito.exists():
    print(f"\n5. ASIGNANDO {categorias_sin_deposito.count()} CATEGORÍAS AL DEPÓSITO CENTRAL:")
    
    with transaction.atomic():
        for categoria in categorias_sin_deposito:
            categoria.deposito = deposito_central
            categoria.save(update_fields=['deposito'])
            print(f"  - Categoría {categoria.nombre} -> {deposito_central.nombre}")

# 6. Verificar insumos con stock bajo en el depósito central
UMBRAL_STOCK_BAJO = 15000
insumos_stock_bajo = Insumo.objects.filter(
    deposito=deposito_central,
    stock__lt=UMBRAL_STOCK_BAJO
)

print(f"\n6. INSUMOS CON STOCK BAJO EN {deposito_central.nombre}:")
print(f"   Umbral: {UMBRAL_STOCK_BAJO}")
print(f"   Insumos críticos: {insumos_stock_bajo.count()}")

for insumo in insumos_stock_bajo[:10]:  # Mostrar solo los primeros 10
    print(f"  - {insumo.descripcion} | Stock: {insumo.stock}")

# 7. Verificar estado final
print(f"\n7. ESTADO FINAL:")
insumos_sin_deposito_final = Insumo.objects.filter(deposito__isnull=True)
print(f"Insumos SIN depósito después de corrección: {insumos_sin_deposito_final.count()}")

for deposito in Deposito.objects.all():
    insumos_del_deposito = Insumo.objects.filter(deposito=deposito)
    insumos_bajo_stock = insumos_del_deposito.filter(stock__lt=UMBRAL_STOCK_BAJO)
    print(f"- {deposito.nombre}: {insumos_del_deposito.count()} insumos, {insumos_bajo_stock.count()} críticos")

# 8. Corregir cantidades de stock de insumos y productos en todos los depósitos
print("\n8. CORRIGIENDO STOCK DE INSUMOS EN TODOS LOS DEPÓSITOS:")
with transaction.atomic():
    for deposito in Deposito.objects.all():
        insumos_stock = StockInsumo.objects.filter(deposito=deposito)
        for stock_insumo in insumos_stock:
            # Actualizar el campo stock del insumo para ese depósito
            insumo = stock_insumo.insumo
            if insumo.deposito == deposito:
                insumo.stock = stock_insumo.cantidad
                insumo.save(update_fields=["stock"])
                print(f"  - {insumo.descripcion} en {deposito.nombre}: stock corregido a {insumo.stock}")

print("\n9. CORRIGIENDO STOCK DE PRODUCTOS TERMINADOS EN TODOS LOS DEPÓSITOS:")
with transaction.atomic():
    for deposito in Deposito.objects.all():
        productos_stock = StockProductoTerminado.objects.filter(deposito=deposito)
        for stock_producto in productos_stock:
            producto = stock_producto.producto
            if producto.deposito == deposito:
                producto.stock = stock_producto.cantidad
                producto.save(update_fields=["stock"])
                print(f"  - {producto.descripcion} en {deposito.nombre}: stock corregido a {producto.stock}")

print("\n=== STOCK DEPOSITOS CORREGIDO ===")
print("\n=== CORRECCIÓN COMPLETADA ===")

# 2. Corregir insumos sin depósito
print("\n2. CORRECCIÓN DE INSUMOS SIN DEPÓSITO:")
with transaction.atomic():
    if insumos_sin_deposito.exists():
        deposito_default = Deposito.objects.first()
        if not deposito_default:
            print("Error: No hay depósitos disponibles para asignar.")
            exit()

        for insumo in insumos_sin_deposito:
            insumo.deposito = deposito_default
            insumo.save()
            print(f"Insumo {insumo.nombre} asignado al depósito {deposito_default.nombre}.")
    else:
        print("No se encontraron insumos sin depósito.")

print("\nCorrección completada con éxito.")
