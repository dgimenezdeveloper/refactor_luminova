

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# --- CONTROL DE CALIDAD (Placeholder) ---
@login_required
def control_calidad_view(request):
    return render(request, "control_calidad/control_calidad.html")
