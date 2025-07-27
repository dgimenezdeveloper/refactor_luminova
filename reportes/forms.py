from django import forms
from .models import ReporteIncidencia

class ReporteIncidenciaForm(forms.ModelForm):
    class Meta:
        model = ReporteIncidencia
        fields = ['deposito', 'tipo', 'descripcion', 'resuelto']
