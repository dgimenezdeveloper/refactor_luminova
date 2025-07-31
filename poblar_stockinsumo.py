# Script para poblar StockInsumo con los insumos y depósitos existentes
# Ejecuta esto con: python manage.py shell < poblar_stockinsumo.py

from App_LUMINOVA.models import Insumo, Deposito, StockInsumo
from django.db import transaction

with transaction.atomic():
    count_created = 0
    for insumo in Insumo.objects.all():
        # Solo crear StockInsumo para el depósito asignado al insumo
        if insumo.deposito:
            stock_obj, created = StockInsumo.objects.get_or_create(
                insumo=insumo,
                deposito=insumo.deposito,
                defaults={"cantidad": insumo.stock or 0}
            )
            if created:
                print(f"Creado StockInsumo para insumo '{insumo.descripcion}' en depósito '{insumo.deposito.nombre}' con cantidad {insumo.stock or 0}")
                count_created += 1
            else:
                # Si ya existe, opcionalmente sincroniza la cantidad
                stock_obj.cantidad = insumo.stock or 0
                stock_obj.save()
                print(f"Actualizado StockInsumo para insumo '{insumo.descripcion}' en depósito '{insumo.deposito.nombre}' a cantidad {insumo.stock or 0}")
    print(f"Total de registros StockInsumo creados/actualizados: {count_created}")
