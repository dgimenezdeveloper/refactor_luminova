#!/usr/bin/env python
"""
Script para asignar todos los insumos a depósitos específicos para propósitos de prueba  
"""

from App_LUMINOVA.models import Insumo, Deposito, CategoriaInsumo
from django.db import transaction

print("=== ASIGNACIÓN ESPECÍFICA DE INSUMOS A DEPÓSITOS ===")

# Obtener depósitos
try:
    central = Deposito.objects.get(nombre="Depósito Central Luminova")
    maestranza = Deposito.objects.get(nombre="Depósito Maestranza")
except Deposito.DoesNotExist:
    print("Error: No se encontraron los depósitos necesarios")
    exit()

print(f"Depósito Central: {central.nombre} (ID: {central.id})")
print(f"Depósito Maestranza: {maestranza.nombre} (ID: {maestranza.id})")

# Verificar estado actual
print(f"\n=== ESTADO ACTUAL POR DEPÓSITO ===")
UMBRAL = 15000

for deposito in [central, maestranza]:
    insumos_deposito = Insumo.objects.filter(deposito=deposito)
    insumos_criticos = insumos_deposito.filter(stock__lt=UMBRAL)
    
    print(f"\n{deposito.nombre}:")
    print(f"  - Total insumos: {insumos_deposito.count()}")
    print(f"  - Insumos críticos (stock < {UMBRAL}): {insumos_criticos.count()}")
    
    if insumos_criticos.exists():
        print(f"  - Lista de críticos:")
        for insumo in insumos_criticos:
            print(f"    · {insumo.descripcion[:50]}... Stock: {insumo.stock}")

# Verificar categorías
print(f"\nVerificando categorías...")
categorias_sin_deposito = CategoriaInsumo.objects.filter(deposito__isnull=True)
if categorias_sin_deposito.exists():
    print(f"Asignando {categorias_sin_deposito.count()} categorías al depósito central:")
    for categoria in categorias_sin_deposito:
        categoria.deposito = central
        categoria.save(update_fields=['deposito'])
        print(f"  ✓ {categoria.nombre} -> {central.nombre}")

print(f"\n✅ Los datos están listos. Ahora prueba la vista del depósito.")
