import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import CategoriaProductoTerminado, Deposito

# Cambia este ID por el del depósito que corresponda
DEPOSITO_ID = 1  # <-- AJUSTA ESTE VALOR

deposito = Deposito.objects.get(id=DEPOSITO_ID)

# Actualiza todas las categorías que no tienen depósito asignado
desactualizadas = CategoriaProductoTerminado.objects.filter(deposito__isnull=True)
for cat in desactualizadas:
    cat.deposito = deposito
    cat.save()
    print(f"Asignada '{cat.nombre}' al depósito {deposito.nombre}")

print(f"Total actualizadas: {desactualizadas.count()}")
