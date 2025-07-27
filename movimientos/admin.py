
from django.contrib import admin
from .models import Movimiento

@admin.register(Movimiento)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ('producto', 'deposito_origen', 'deposito_destino', 'tipo', 'cantidad', 'usuario', 'fecha')
    search_fields = ('producto__nombre', 'deposito_origen__nombre', 'deposito_destino__nombre', 'usuario__username')
