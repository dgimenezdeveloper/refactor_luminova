import os
import django
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import CategoriaProductoTerminado, Deposito

if len(sys.argv) < 2:
    print("Uso: python asignar_deposito_categorias_pt.py <DEPOSITO_ID>")
    exit()

try:
    DEPOSITO_ID = int(sys.argv[1])
    deposito = Deposito.objects.get(id=DEPOSITO_ID)
except ValueError:
    print("Error: El ID del depósito debe ser un número entero.")
    exit()
except Deposito.DoesNotExist:
    print(f"Error: No se encontró un depósito con ID {DEPOSITO_ID}.")
    exit()

desactualizadas = CategoriaProductoTerminado.objects.filter(deposito__isnull=True)
if desactualizadas.exists():
    for cat in desactualizadas:
        cat.deposito = deposito
        cat.save()
        print(f"Asignada '{cat.nombre}' al depósito {deposito.nombre}")
    print(f"Total actualizadas: {desactualizadas.count()}")
else:
    print("No se encontraron categorías sin depósito asignado.")
