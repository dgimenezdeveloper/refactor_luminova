
from django.contrib import admin
from .models import ReporteIncidencia

@admin.register(ReporteIncidencia)
class ReporteIncidenciaAdmin(admin.ModelAdmin):
    list_display = ('deposito', 'usuario', 'tipo', 'resuelto', 'fecha_reporte', 'fecha_resolucion')
    search_fields = ('deposito__nombre', 'usuario__username', 'tipo')
