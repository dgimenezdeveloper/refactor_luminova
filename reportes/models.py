
from django.db import models
from django.contrib.auth.models import User
from depositos.models import Deposito

class ReporteIncidencia(models.Model):
    TIPO_CHOICES = [
        ("stock", "Problema de Stock"),
        ("calidad", "Problema de Calidad"),
        ("sistema", "Incidencia de Sistema"),
        ("otro", "Otro"),
    ]
    deposito = models.ForeignKey(Deposito, on_delete=models.SET_NULL, null=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    descripcion = models.TextField()
    resuelto = models.BooleanField(default=False)
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Reporte {self.tipo} en {self.deposito} por {self.usuario}"
