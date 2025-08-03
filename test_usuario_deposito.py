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
from App_LUMINOVA.models import Deposito, UsuarioDeposito

def test_usuario_deposito_functionality():
    print("=== Prueba de Funcionalidad Usuario-Depósito ===")
    
    # Verificar que existan depósitos
    depositos = Deposito.objects.all()
    print(f"Depósitos disponibles: {depositos.count()}")
    for deposito in depositos:
        print(f"  - {deposito.nombre} ({deposito.ubicacion})")
    
    # Verificar usuarios con rol Depósito
    grupo_deposito = Group.objects.filter(name='Depósito').first()
    if grupo_deposito:
        usuarios_deposito = User.objects.filter(groups=grupo_deposito)
        print(f"\nUsuarios con rol Depósito: {usuarios_deposito.count()}")
        for usuario in usuarios_deposito:
            print(f"  - {usuario.username}")
            asignaciones = UsuarioDeposito.objects.filter(usuario=usuario)
            print(f"    Depósitos asignados: {asignaciones.count()}")
            for asignacion in asignaciones:
                print(f"      * {asignacion.deposito.nombre} - T:{asignacion.puede_transferir} E:{asignacion.puede_entradas} S:{asignacion.puede_salidas}")
    else:
        print("\nNo existe el grupo 'Depósito'")
    
    print("\n=== Prueba completada ===")

if __name__ == "__main__":
    test_usuario_deposito_functionality()
