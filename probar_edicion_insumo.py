#!/usr/bin/env python3
"""
Script para probar la edición de insumos y verificar que mantienen su depósito
"""
import os
import sys
import django
from django.conf import settings

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import Insumo, Deposito
from App_LUMINOVA.forms import InsumoForm

def main():
    print("=== PRUEBA DE EDICIÓN DE INSUMOS ===\n")
    
    # Obtener el depósito central
    try:
        deposito_central = Deposito.objects.get(nombre="Depósito Central Luminova")
        print(f"✅ Depósito encontrado: {deposito_central.nombre}")
    except Deposito.DoesNotExist:
        print("❌ No se encontró el Depósito Central Luminova")
        return
    
    # Buscar un insumo crítico para probar
    insumo_critico = Insumo.objects.filter(
        deposito=deposito_central,
        stock__lte=15000
    ).first()
    
    if not insumo_critico:
        print("❌ No se encontró un insumo crítico para probar")
        return
    
    print(f"📦 Insumo a probar: {insumo_critico.descripcion}")
    print(f"   Stock actual: {insumo_critico.stock}")
    print(f"   Depósito actual: {insumo_critico.deposito.nombre}")
    
    # Preparar datos para el formulario (simulando edición)
    datos_formulario = {
        'descripcion': insumo_critico.descripcion,
        'categoria': insumo_critico.categoria.id if insumo_critico.categoria else '',
        'fabricante': insumo_critico.fabricante.id if insumo_critico.fabricante else '',
        'stock': insumo_critico.stock - 500,  # Reducir stock para simular edición
        'cantidad_en_pedido': insumo_critico.cantidad_en_pedido or 0,
    }
    
    print(f"\n🔄 Simulando edición con nuevo stock: {datos_formulario['stock']}")
    
    # Crear formulario con los datos
    form = InsumoForm(data=datos_formulario, instance=insumo_critico)
    
    print(f"📝 Formulario válido: {form.is_valid()}")
    
    if not form.is_valid():
        print("❌ Errores en el formulario:")
        for campo, errores in form.errors.items():
            print(f"   {campo}: {errores}")
        return
    
    # Verificar si el depósito se mantiene
    print(f"🏪 Depósito en instancia antes de save: {insumo_critico.deposito.nombre}")
    
    # Simular guardado (pero sin hacerlo realmente)
    insumo_actualizado = form.save(commit=False)
    print(f"🏪 Depósito después de form.save(commit=False): {insumo_actualizado.deposito}")
    
    if insumo_actualizado.deposito is None:
        print("❌ PROBLEMA: El depósito se perdió durante la edición")
        print("🔧 El formulario necesita preservar el depósito original")
    else:
        print(f"✅ El depósito se mantiene: {insumo_actualizado.deposito.nombre}")
    
    print("\n=== RESUMEN ===")
    print(f"- Stock original: {insumo_critico.stock}")
    print(f"- Stock nuevo: {datos_formulario['stock']}")
    print(f"- Depósito preservado: {'✅ Sí' if insumo_actualizado.deposito else '❌ No'}")

if __name__ == "__main__":
    main()
