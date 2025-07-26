from django import forms
from insumos.models import Insumo

class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        # Incluye solo los campos válidos del modelo Insumo
        fields = [
            "nombre",
            "descripcion",
            "categoria",
            "fabricante",
            "proveedor",
            "unidad_medida",
            "cantidad",
        ]
