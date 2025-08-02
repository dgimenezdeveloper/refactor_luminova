#!/usr/bin/env python3
"""
Script para simular la vista de notificación y verificar que funciona
"""
import os
import sys
import django
from django.conf import settings

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from App_LUMINOVA.models import Insumo, Deposito
from App_LUMINOVA.views_deposito import notificar_stock_bajo_view
import json

def main():
    print("=== SIMULACIÓN DE NOTIFICACIÓN ===\n")
    
    # Crear una request factory
    factory = RequestFactory()
    
    # Obtener un usuario para la prueba
    try:
        usuario = User.objects.first()
        print(f"✅ Usuario para prueba: {usuario.username}")
    except Exception as e:
        print(f"❌ Error al obtener usuario: {e}")
        return
    
    # Obtener el depósito central
    try:
        deposito_central = Deposito.objects.get(nombre="Depósito Central Luminova")
        print(f"✅ Depósito encontrado: {deposito_central.nombre} (ID: {deposito_central.id})")
    except Exception as e:
        print(f"❌ Error al obtener depósito: {e}")
        return
    
    # Buscar un insumo crítico
    try:
        insumo_critico = Insumo.objects.filter(
            deposito=deposito_central,
            stock__lte=15000
        ).first()
        
        if not insumo_critico:
            print("❌ No se encontró un insumo crítico")
            return
            
        print(f"📦 Insumo crítico: {insumo_critico.descripcion} (ID: {insumo_critico.id})")
        print(f"   Stock: {insumo_critico.stock}")
        print(f"   Depósito: {insumo_critico.deposito.nombre}")
    except Exception as e:
        print(f"❌ Error al obtener insumo: {e}")
        return
    
    # Simular la petición HTTP POST
    print("\n🔔 Simulando petición de notificación...")
    
    # Crear request POST
    request = factory.post(f'/deposito/notificar-stock-bajo/{insumo_critico.id}/', 
                          data='{}', 
                          content_type='application/json')
    request.user = usuario
    
    # Caso 1: Sin depósito en sesión (debería usar el del insumo)
    print("\n1️⃣ Prueba sin depósito en sesión:")
    request.session = {}
    
    try:
        response = notificar_stock_bajo_view(request, insumo_critico.id)
        
        if hasattr(response, 'content'):
            response_data = json.loads(response.content.decode())
            if response_data.get('success'):
                print(f"✅ Notificación exitosa: {response_data.get('message')}")
            else:
                print(f"❌ Error en notificación: {response_data.get('error')}")
        else:
            print(f"❌ Respuesta inesperada: {response}")
            
    except Exception as e:
        print(f"❌ Error al procesar notificación: {e}")
        import traceback
        traceback.print_exc()
    
    # Caso 2: Con depósito en sesión
    print("\n2️⃣ Prueba con depósito en sesión:")
    request.session = {'deposito_seleccionado': deposito_central.id}
    
    try:
        response = notificar_stock_bajo_view(request, insumo_critico.id)
        
        if hasattr(response, 'content'):
            response_data = json.loads(response.content.decode())
            if response_data.get('success'):
                print(f"✅ Notificación exitosa: {response_data.get('message')}")
            else:
                print(f"❌ Error en notificación: {response_data.get('error')}")
        else:
            print(f"❌ Respuesta inesperada: {response}")
            
    except Exception as e:
        print(f"❌ Error al procesar notificación: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
