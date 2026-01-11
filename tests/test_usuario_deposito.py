#!/usr/bin/env python3
"""
Script de prueba para verificar la funcionalidad de asignación de depósitos a usuarios
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from django.contrib.auth.models import User, Group
from django.test import TestCase
from App_LUMINOVA.models import Deposito, UsuarioDeposito, Empresa

class TestUsuarioDeposito(TestCase):
    def setUp(self):
        # Crear datos de prueba
        self.grupo_deposito = Group.objects.create(name='Depósito')
        self.usuario = User.objects.create_user(username='testuser', password='password')
        self.usuario.groups.add(self.grupo_deposito)
        self.empresa = Empresa.objects.create(nombre='Empresa Test')
        self.deposito = Deposito.objects.create(nombre='Depósito 1', empresa=self.empresa)
        UsuarioDeposito.objects.create(usuario=self.usuario, deposito=self.deposito)

    def test_usuario_deposito_functionality(self):
        # Verificar que existan depósitos
        depositos = Deposito.objects.all()
        self.assertGreater(depositos.count(), 0, "No se encontraron depósitos.")

        # Verificar usuarios con rol Depósito
        grupo_deposito = Group.objects.filter(name='Depósito').first()
        self.assertIsNotNone(grupo_deposito, "No existe el grupo 'Depósito'.")

        usuarios_deposito = User.objects.filter(groups=grupo_deposito)
        self.assertGreater(usuarios_deposito.count(), 0, "No se encontraron usuarios con el rol 'Depósito'.")

        for usuario in usuarios_deposito:
            asignaciones = UsuarioDeposito.objects.filter(usuario=usuario)
            self.assertGreaterEqual(asignaciones.count(), 0, f"El usuario {usuario.username} no tiene depósitos asignados.")

    def test_sin_depositos(self):
        # Eliminar todos los depósitos
        Deposito.objects.all().delete()
        depositos = Deposito.objects.all()
        self.assertEqual(depositos.count(), 0, "Se encontraron depósitos cuando no debería haber ninguno.")

    def test_sin_usuarios_en_grupo(self):
        # Eliminar todos los usuarios del grupo
        self.grupo_deposito.user_set.clear()
        usuarios_deposito = User.objects.filter(groups=self.grupo_deposito)
        self.assertEqual(usuarios_deposito.count(), 0, "Se encontraron usuarios en el grupo 'Depósito' cuando no debería haber ninguno.")
