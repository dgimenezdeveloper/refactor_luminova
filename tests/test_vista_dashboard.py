#!/usr/bin/env python
"""
Script para probar la vista del dashboard directamente
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.views_producción import produccion_stock_dashboard_view
from django.test import RequestFactory
from django.contrib.auth.models import User

def test_dashboard_view():
    print("=== PRUEBA VISTA DASHBOARD ===")
    
    # Crear request factory
    factory = RequestFactory()
    request = factory.get('/produccion/produccion/stock/dashboard/')
    
    # Obtener usuario
    user = User.objects.first()
    request.user = user
    
    try:
        # Ejecutar vista
        response = produccion_stock_dashboard_view(request)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Vista ejecutada exitosamente")
            
            # Verificar contenido
            content = response.content.decode('utf-8')
            
            if 'productos-table' in content:
                print("✅ Tabla de productos encontrada en el HTML")
            else:
                print("❌ Tabla de productos NO encontrada en el HTML")
                
            if 'clickable-card' in content:
                print("✅ Tarjetas clickeables encontradas en el HTML")
            else:
                print("❌ Tarjetas clickeables NO encontradas en el HTML")
                
            if 'generar-ops-automaticas' in content:
                print("✅ Botón de generar OPs automáticas encontrado")
            else:
                print("❌ Botón de generar OPs automáticas NO encontrado")
                
        else:
            print(f"❌ Error en la vista: Status {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error ejecutando vista: {e}")

if __name__ == '__main__':
    test_dashboard_view()
