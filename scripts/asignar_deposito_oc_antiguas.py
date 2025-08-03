# Script para asignar el depósito correcto a las OCs antiguas (deposito=NULL)
# Ejecutar con: python manage.py shell < scripts/asignar_deposito_oc_antiguas.py

from App_LUMINOVA.models import Orden
from django.db import transaction

actualizadas = 0
sin_insumo = 0
sin_deposito = 0

with transaction.atomic():
    ocs = Orden.objects.filter(deposito__isnull=True)
    for oc in ocs:
        insumo = oc.insumo_principal
        if not insumo:
            sin_insumo += 1
            continue
        deposito = getattr(insumo, 'deposito', None)
        if deposito:
            oc.deposito = deposito
            oc.save(update_fields=['deposito'])
            actualizadas += 1
        else:
            sin_deposito += 1

print(f"Órdenes actualizadas: {actualizadas}")
print(f"Órdenes sin insumo principal: {sin_insumo}")
print(f"Órdenes cuyo insumo no tiene depósito: {sin_deposito}")
print("Listo. Verifica los resultados y repite si agregas depósitos a insumos.")
