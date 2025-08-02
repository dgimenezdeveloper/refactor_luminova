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
        for insumo in insumos_sin_deposito[:5]:
            print(f"      - {insumo.descripcion}")
    else:
        print("   ✅ Todos los insumos tienen depósito asignado")
    
    # 2. Verificar insumos con stock crítico en Depósito Central Luminova
    try:
        deposito_central = Deposito.objects.get(nombre="Depósito Central Luminova")
        insumos_criticos = Insumo.objects.filter(
            deposito=deposito_central,
            stock__lte=15000
        ).order_by('stock')
        
        print(f"\n2. Insumos con stock crítico en {deposito_central.nombre}: {insumos_criticos.count()}")
        
        if insumos_criticos.exists():
            print("   📋 Lista de insumos críticos:")
            for insumo in insumos_criticos:
                print(f"      - {insumo.descripcion}: {insumo.stock} unidades")
        else:
            print("   ✅ No hay insumos con stock crítico")
            
    except Deposito.DoesNotExist:
        print("   ❌ No se encontró el Depósito Central Luminova")
    
    # 3. Resumen por depósito
    print(f"\n3. Resumen por depósito:")
    for deposito in Deposito.objects.all():
        total_insumos = Insumo.objects.filter(deposito=deposito).count()
        criticos = Insumo.objects.filter(deposito=deposito, stock__lte=15000).count()
        print(f"   - {deposito.nombre}: {total_insumos} insumos ({criticos} críticos)")

if __name__ == "__main__":
    verificar_estado()
