#!/usr/bin/env python
"""
Script de prueba para verificar la funcionalidad de redirección de roles
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.test import TestCase
from App_LUMINOVA.utils import redirigir_segun_rol

class TestRedirection(TestCase):
    def setUp(self):
        # Crear datos de prueba
        self.usuario_admin = User.objects.create_user(username='admin', password='password')
        self.grupo_admin = Group.objects.create(name='Admin')
        self.usuario_admin.groups.add(self.grupo_admin)

    def test_redirection(self):
        """Prueba la funcionalidad de redirección por roles"""

        # Crear grupos de prueba si no existen
        print("=== TEST REDIRECCIÓN ===")
        groups = ['compras', 'ventas', 'produccion', 'control de calidad', 'depósito', 'administrador']
        for group_name in groups:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                print(f"✓ Grupo '{group_name}' creado")
            else:
                print(f"✓ Grupo '{group_name}' ya existe")
        
        # Crear usuario de prueba
        test_user, created = User.objects.get_or_create(
            username='test_deposito_user',
            defaults={'email': 'test@example.com'}
        )
        if created:
            print("✓ Usuario de prueba creado")
        else:
            print("✓ Usuario de prueba ya existe")
        
        # Asignar grupo depósito
        deposito_group = Group.objects.get(name='depósito')
        test_user.groups.clear()
        test_user.groups.add(deposito_group)
        print(f"✓ Usuario asignado al grupo '{deposito_group.name}'")
        
        # Simular request object básico
        class MockRequest:
            def __init__(self):
                self.META = {}
        
        # Simular redirección
        print("\n--- Simulando redirección ---")
        print(f"Usuario: {test_user.username}")
        print(f"Grupos: {[g.name for g in test_user.groups.all()]}")
        
        # La función redirigir_segun_rol retorna un HttpResponseRedirect
        response = redirigir_segun_rol(test_user)
        print(f"✓ Redirección generada: {response}")
        print(f"✓ URL de redirección: {response.url}")
        
        # Probar redirección según rol
        url = redirigir_segun_rol(self.usuario_admin)
        self.assertEqual(url, '/admin/dashboard', "La redirección para el rol Admin no es correcta.")
        
        # Limpiar
        test_user.delete()
        print("\n✓ Usuario de prueba eliminado")
        
        print("\n=== PRUEBA COMPLETADA EXITOSAMENTE ===")
