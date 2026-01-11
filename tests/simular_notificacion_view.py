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
    print("=== SIMULACIÓN DE VISTA DE NOTIFICACIÓN ===")

    # Crear datos de prueba
    usuario = User.objects.create_user(username='testuser', password='password')
    deposito = Deposito.objects.create(nombre='Depósito Prueba')
    insumo = Insumo.objects.create(nombre='Insumo Prueba', cantidad=5, deposito=deposito)

    # Crear solicitud simulada
    factory = RequestFactory()
    request = factory.get('/notificar_stock_bajo')
    request.user = usuario

    # Llamar a la vista
    response = notificar_stock_bajo_view(request)

    # Validar respuesta
    print(f"Código de respuesta: {response.status_code}")
    print(f"Contenido de la respuesta: {response.content.decode()}")

if __name__ == "__main__":
    main()
