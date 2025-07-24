# Script para migrar depósitos y stock desde App_LUMINOVA a depositos
from django.core.management import setup_environ
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from Proyecto_LUMINOVA import settings
setup_environ(settings)

from App_LUMINOVA.models import Deposito as DepositoViejo, StockProductoTerminado as StockViejo
from depositos.models import Deposito as DepositoNuevo, StockProductoTerminado as StockNuevo
from productos.models import ProductoTerminado

# Migrar depósitos
for dep in DepositoViejo.objects.all():
    if not DepositoNuevo.objects.filter(nombre=dep.nombre).exists():
        nuevo = DepositoNuevo(nombre=dep.nombre, ubicacion=dep.ubicacion, descripcion=dep.descripcion)
        nuevo.save()
        print(f"Migrado depósito: {dep.nombre}")

# Migrar stock de productos terminados por depósito
for stock in StockViejo.objects.all():
    try:
        producto = ProductoTerminado.objects.get(descripcion=stock.producto.descripcion)
        deposito = DepositoNuevo.objects.get(nombre=stock.deposito.nombre)
        if not StockNuevo.objects.filter(producto=producto, deposito=deposito).exists():
            nuevo_stock = StockNuevo(producto=producto, deposito=deposito, cantidad=stock.cantidad)
            nuevo_stock.save()
            print(f"Migrado stock: {producto} en {deposito}")
    except Exception as e:
        print(f"Error migrando stock: {e}")

print("Migración finalizada.")
