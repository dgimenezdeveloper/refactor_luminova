
from django.contrib import admin
from .models import ProductoTerminado, CategoriaProductoTerminado

@admin.register(ProductoTerminado)
class ProductoTerminadoAdmin(admin.ModelAdmin):
    list_display = ("descripcion", "categoria", "precio_unitario", "modelo", "potencia", "acabado", "color_luz", "material")
    search_fields = ("descripcion", "modelo")

@admin.register(CategoriaProductoTerminado)
class CategoriaProductoTerminadoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)
