
from django.contrib import admin
from .models import Deposito, StockProductoTerminado

@admin.register(Deposito)
class DepositoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "ubicacion", "descripcion")
    search_fields = ("nombre", "ubicacion")

@admin.register(StockProductoTerminado)
class StockProductoTerminadoAdmin(admin.ModelAdmin):
    list_display = ("producto", "deposito", "cantidad")
    list_filter = ("deposito", "producto")
