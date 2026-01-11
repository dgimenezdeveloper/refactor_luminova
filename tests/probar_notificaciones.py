#!/usr/bin/env python3
"""
Script para probar la funcionalidad de notificaciones
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
from App_LUMINOVA.services.notification_service import NotificationService
from django.contrib.auth.models import User

def main():
    print("=== PRUEBA DE NOTIFICACIONES ===\n")
    
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
        print(f"✅ Depósito encontrado: {deposito_central.nombre}")
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
            
        print(f"📦 Insumo crítico: {insumo_critico.descripcion}")
        print(f"   Stock: {insumo_critico.stock}")
    except Exception as e:
        print(f"❌ Error al obtener insumo: {e}")
        return
    
    # Probar el servicio de notificaciones
    try:
        print("\n🔔 Probando NotificationService...")
        
        notificacion = NotificationService.notificar_stock_bajo(
            insumo=insumo_critico,
            deposito=deposito_central,
            usuario_remitente=usuario,
            umbral_critico=15000
        )
        
        print(f"✅ Notificación creada exitosamente:")
        print(f"   ID: {notificacion.id}")
        print(f"   Tipo: {notificacion.tipo}")
        print(f"   Título: {notificacion.titulo}")
        print(f"   Estado: {notificacion.estado}")
        
    except Exception as e:
        print(f"❌ Error al crear notificación: {e}")
        import traceback
        traceback.print_exc()

    # Crear un usuario de prueba
    usuario_prueba = User.objects.create_user(username='notificador', password='password')
    print(f"✅ Usuario de prueba creado: {usuario_prueba.username}")

    # Crear un insumo de prueba
    insumo_prueba = Insumo.objects.create(nombre='Insumo Prueba', cantidad=10)
    print(f"✅ Insumo de prueba creado: {insumo_prueba.nombre}")

    # Crear un depósito de prueba
    deposito_prueba = Deposito.objects.create(nombre='Depósito Prueba')
    print(f"✅ Depósito de prueba creado: {deposito_prueba.nombre}")

    # Probar la creación de una notificación
    servicio_notificaciones = NotificationService()
    notificacion_prueba = servicio_notificaciones.crear_notificacion(
        usuario=usuario_prueba,
        mensaje='Prueba de notificación',
        tipo='INFO'
    )

    print(f"✅ Notificación de prueba creada: {notificacion_prueba}")

    # Validar que la notificación se guardó correctamente
    assert notificacion_prueba.id is not None, "La notificación no se guardó correctamente."

if __name__ == "__main__":
    main()
