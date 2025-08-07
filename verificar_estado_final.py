#!/usr/bin/env python
"""
Script para verificar y asignar stock de insumos a depósitos específicos para propósitos de prueba  
"""

from App_LUMINOVA.models import Insumo, Deposito, CategoriaInsumo, StockInsumo
from django.db import transaction

print("=== VERIFICACIÓN Y ASIGNACIÓN DE STOCK DE INSUMOS A DEPÓSITOS ===")

# Obtener depósitos
try:
    central = Deposito.objects.get(nombre="Depósito Central Luminova")
    maestranza = Deposito.objects.get(nombre="Depósito Maestranza")
except Deposito.DoesNotExist:
    print("Error: No se encontraron los depósitos necesarios")
    exit()

print(f"Depósito Central: {central.nombre} (ID: {central.id})")
print(f"Depósito Maestranza: {maestranza.nombre} (ID: {maestranza.id})")

# Verificar estado actual de stock por depósito
print(f"\n=== ESTADO ACTUAL DE STOCK POR DEPÓSITO ===")
UMBRAL = 15000

for deposito in [central, maestranza]:
    stock_deposito = StockInsumo.objects.filter(deposito=deposito)
    insumos_criticos = stock_deposito.filter(cantidad__lt=UMBRAL)
    
    print(f"\n{deposito.nombre}:")
    print(f"  - Total insumos con stock: {stock_deposito.count()}")
    print(f"  - Insumos críticos (stock < {UMBRAL}): {insumos_criticos.count()}")
    
    if insumos_criticos.exists():
        print(f"  - Lista de críticos:")
        for stock in insumos_criticos:
            print(f"    · {stock.insumo.descripcion[:50]}... Stock: {stock.cantidad}")

# Verificar categorías (solo si CategoriaInsumo tiene campo deposito)
if hasattr(CategoriaInsumo, 'deposito'):
    print(f"\nVerificando categorías...")
    categorias_sin_deposito = CategoriaInsumo.objects.filter(deposito__isnull=True)
    if categorias_sin_deposito.exists():
        print(f"Asignando {categorias_sin_deposito.count()} categorías al depósito central:")
        for categoria in categorias_sin_deposito:
            categoria.deposito = central
            categoria.save(update_fields=['deposito'])
            print(f"  ✓ {categoria.nombre} -> {central.nombre}")

# Asignar stock de insumos a depósitos (ejemplo de distribución)
with transaction.atomic():
    insumos = Insumo.objects.all()
    if not insumos.exists():
        print("No se encontraron insumos para asignar.")
        exit()

    for insumo in insumos:
        # Asignar stock a depósitos según alguna lógica de prueba
        # Puedes personalizar esta lógica según tus necesidades reales
        if hasattr(insumo, "categoria") and getattr(insumo.categoria, "nombre", "") == "Categoría A":
            deposito = central
        else:
            deposito = maestranza

        # Crear o actualizar el stock en el depósito correspondiente
        stock_obj, created = StockInsumo.objects.get_or_create(
            insumo=insumo,
            deposito=deposito,
            defaults={'cantidad': insumo.stock or 0}
        )
        if not created:
            stock_obj.cantidad = insumo.stock or 0
            stock_obj.save(update_fields=['cantidad'])
        print(f"Insumo {insumo.descripcion} asignado a {deposito.nombre} con stock {stock_obj.cantidad}.")

print("\n=== PROCESO COMPLETADO ===")
print("✅ Los datos están listos. Ahora prueba la vista del depósito.")
