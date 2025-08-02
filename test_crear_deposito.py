#!/usr/bin/env python
import os
import sys
import django

# Agregar el directorio del proyecto al path
sys.path.insert(0, '/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import Deposito
from App_LUMINOVA.forms import DepositoForm

def test_crear_deposito():
    print("=== TEST CREAR DEPÓSITO ===")
    
    # 1. Verificar que el modelo Deposito existe y funciona
    print(f"Depósitos existentes: {Deposito.objects.count()}")
    for dep in Deposito.objects.all():
        print(f"  - {dep.id}: {dep.nombre}")
    
    # 2. Probar el formulario
    print("\n=== PROBANDO FORMULARIO ===")
    datos_test = {
        'nombre': 'Depósito de Prueba',
        'ubicacion': 'Ubicación de Prueba',
        'descripcion': 'Descripción de Prueba'
    }
    
    form = DepositoForm(datos_test)
    print(f"Formulario es válido: {form.is_valid()}")
    
    if form.is_valid():
        print("Creando depósito...")
        deposito = form.save()
        print(f"Depósito creado con ID: {deposito.id}, Nombre: {deposito.nombre}")
        
        # Limpiar
        deposito.delete()
        print("Depósito de prueba eliminado")
    else:
        print(f"Errores del formulario: {form.errors}")
    
    print("\n=== TEST COMPLETADO ===")

if __name__ == '__main__':
    test_crear_deposito()
