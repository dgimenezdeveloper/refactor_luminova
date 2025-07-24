
from django.db import models

class Deposito(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    ubicacion = models.CharField(max_length=255, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Depósito"
        verbose_name_plural = "Depósitos"

    def __str__(self):
        return self.nombre

class StockProductoTerminado(models.Model):
    # La relación con ProductoTerminado se mantiene, pero el modelo debe migrarse a productos/models.py
    producto = models.ForeignKey('productos.ProductoTerminado', on_delete=models.CASCADE, related_name='stocks')
    deposito = models.ForeignKey('depositos.Deposito', on_delete=models.CASCADE, related_name='stocks_productos')
    cantidad = models.IntegerField(default=0)

    class Meta:
        unique_together = ('producto', 'deposito')
        verbose_name = "Stock de Producto Terminado por Depósito"
        verbose_name_plural = "Stocks de Productos Terminados por Depósito"

    def __str__(self):
        return f"{self.producto} en {self.deposito}: {self.cantidad}"
