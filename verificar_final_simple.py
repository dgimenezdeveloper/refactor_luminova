#!/usr/bin/env python3
import os
import django
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import Insumo, Deposito

def verificar_estado():
    print("=== VERIFICACIÓN FINAL DEL SISTEMA ===\n")
    
    # 1. Verificar que no hay insumos sin depósito
    insumos_sin_deposito = Insumo.objects.filter(deposito__isnull=True)
    print(f"1. Insumos sin depósito: {insumos_sin_deposito.count()}")
    
    if insumos_sin_deposito.exists():
        print("   ❌ PROBLEMA: Hay insumos sin depósito:")
        for insumo in insumos_sin_deposito:
            print(f"      - Insumo: {insumo.nombre}")
    else:
        print("   ✅ Todos los insumos tienen depósito asignado.")

    # 2. Verificar depósitos sin insumos
    depositos_sin_insumos = Deposito.objects.filter(insumo__isnull=True)
    print(f"2. Depósitos sin insumos: {depositos_sin_insumos.count()}")

    if depositos_sin_insumos.exists():
        print("   ❌ PROBLEMA: Hay depósitos sin insumos:")
        for deposito in depositos_sin_insumos:
            print(f"      - Depósito: {deposito.nombre}")
    else:
        print("   ✅ Todos los depósitos tienen al menos un insumo asignado.")

    print("\n=== VERIFICACIÓN COMPLETADA ===")

if __name__ == "__main__":
    verificar_estado()
