from django import forms
from .models import Movimiento

class MovimientoForm(forms.ModelForm):
    class Meta:
        model = Movimiento
        fields = ['producto', 'deposito_origen', 'deposito_destino', 'tipo', 'cantidad', 'notas']
