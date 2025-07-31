from django.core.management.base import BaseCommand
from App_LUMINOVA.models import Insumo, ProductoTerminado, Deposito, StockInsumo, StockProductoTerminado

class Command(BaseCommand):
    help = 'Sincroniza el stock actual de Insumos y Productos Terminados al modelo multidepósito'

    def handle(self, *args, **options):
        deposito_principal = Deposito.objects.first()
        if not deposito_principal:
            self.stdout.write(self.style.ERROR('No hay depósitos registrados.'))
            return

        # Sincronizar Insumos
        insumos_migrados = 0
        for insumo in Insumo.objects.all():
            StockInsumo.objects.update_or_create(
                insumo=insumo,
                deposito=deposito_principal,
                defaults={'cantidad': insumo.stock}
            )
            insumos_migrados += 1

        # Sincronizar Productos Terminados
        productos_migrados = 0
        for producto in ProductoTerminado.objects.all():
            StockProductoTerminado.objects.update_or_create(
                producto=producto,
                deposito=deposito_principal,
                defaults={'cantidad': producto.stock}
            )
            productos_migrados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Stock sincronizado: {insumos_migrados} insumos y {productos_migrados} productos terminados en el depósito "{deposito_principal.nombre}".'
        ))