from django.db import models
from django.contrib.auth.models import User
from insumos.models import Insumo, Proveedor

class OrdenCompra(models.Model):
    ESTADO_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("APROBADA", "Aprobada"),
        ("ENVIADA", "Enviada al Proveedor"),
        ("RECIBIDA", "Recibida"),
        ("CANCELADA", "Cancelada"),
    ]
    insumo = models.ForeignKey(Insumo, on_delete=models.PROTECT)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="BORRADOR")
    usuario_solicitante = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_recibida = models.DateTimeField(null=True, blank=True)
    notas = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"OC: {self.insumo} x {self.cantidad} ({self.proveedor})"
