
from django.db import models
from django.contrib.auth.models import User
from depositos.models import Deposito
from productos.models import ProductoTerminado

class Movimiento(models.Model):
    TIPO_CHOICES = [
        ("entrada", "Entrada"),
        ("salida", "Salida"),
        ("transferencia", "Transferencia entre depósitos"),
    ]
    producto = models.ForeignKey(ProductoTerminado, on_delete=models.CASCADE)
    deposito_origen = models.ForeignKey(Deposito, on_delete=models.CASCADE, related_name="movimientos_origen", null=True, blank=True)
    deposito_destino = models.ForeignKey(Deposito, on_delete=models.CASCADE, related_name="movimientos_destino", null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.PositiveIntegerField()
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.tipo} de {self.cantidad} {self.producto} ({self.deposito_origen} → {self.deposito_destino})"
