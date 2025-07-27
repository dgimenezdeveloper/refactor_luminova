from django import forms
from .models import OrdenCompra

class OrdenCompraForm(forms.ModelForm):
    class Meta:
        model = OrdenCompra
        fields = ['insumo', 'proveedor', 'cantidad', 'precio_unitario', 'notas']
