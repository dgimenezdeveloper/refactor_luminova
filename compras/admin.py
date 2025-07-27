from django.contrib import admin
from .models import OrdenCompra

@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('insumo', 'proveedor', 'cantidad', 'precio_unitario', 'estado', 'usuario_solicitante', 'fecha_creacion')
    search_fields = ('insumo__nombre', 'proveedor__nombre', 'usuario_solicitante__username')
