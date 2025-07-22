from django.db import migrations

def inicializar_stock_por_deposito(apps, schema_editor):
    Deposito = apps.get_model('App_LUMINOVA', 'Deposito')
    ProductoTerminado = apps.get_model('App_LUMINOVA', 'ProductoTerminado')
    StockProductoTerminado = apps.get_model('App_LUMINOVA', 'StockProductoTerminado')

    # Crear depósito principal
    deposito, created = Deposito.objects.get_or_create(
        nombre='Depósito Central', defaults={'ubicacion': 'Principal', 'descripcion': 'Depósito migrado automáticamente'}
    )

    # Migrar stock de cada producto terminado
    for producto in ProductoTerminado.objects.all():
        StockProductoTerminado.objects.create(
            producto=producto,
            deposito=deposito,
            cantidad=producto.stock
        )

class Migration(migrations.Migration):
    dependencies = [
        ('App_LUMINOVA', '0018_passwordchangerequired'),
    ]

    operations = [
        migrations.RunPython(inicializar_stock_por_deposito),
    ]
