from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('App_LUMINOVA', '0009_alter_insumo_cantidad_en_pedido'),
    ]

    operations = [
        migrations.AddField(
            model_name='orden',
            name='deposito',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='ordenes_de_compra',
                to='App_LUMINOVA.deposito',
                verbose_name='Depósito que solicita',
                help_text='Depósito que origina la solicitud de compra',
            ),
        ),
    ]
