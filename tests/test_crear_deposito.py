#!/usr/bin/env python
import os
import sys
import django
from django.test import TestCase

# Agregar el directorio del proyecto al path
sys.path.insert(0, '/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import Deposito, Empresa
from App_LUMINOVA.forms import DepositoForm

class TestCrearDeposito(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre="Empresa Test")
        # Configurar datos de prueba
        self.datos_formulario = {
            'nombre': 'Depósito Prueba',
            'ubicacion': 'Ubicación Prueba'
        }

    def test_crear_deposito(self):
        print("=== TEST CREAR DEPÓSITO ===")

        # 1. Verificar que el modelo Deposito existe y funciona
        print(f"Depósitos existentes: {Deposito.objects.count()}")
        for dep in Deposito.objects.all():
            print(f"  - {dep.id}: {dep.nombre}")
        
        # 2. Probar el formulario
        print("\n=== PROBANDO FORMULARIO ===")
        form = DepositoForm(data=self.datos_formulario)
        print(f"Formulario es válido: {form.is_valid()}")
        
        if form.is_valid():
            print("Creando depósito...")
            deposito = form.save(commit=False)
            deposito.empresa = self.empresa
            deposito.save()
            print(f"Depósito creado con ID: {deposito.id}, Nombre: {deposito.nombre}")
            
            # Verificar que el depósito se haya creado correctamente
            self.assertIsNotNone(deposito.id, "El depósito no se creó correctamente en la base de datos.")
            
            # Limpiar
            deposito.delete()
            print("Depósito de prueba eliminado")
        else:
            print(f"Errores del formulario: {form.errors}")
        
        print("\n=== TEST COMPLETADO ===")
