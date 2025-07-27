

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import ReporteIncidencia
from .forms import ReporteIncidenciaForm

@login_required
def lista_reportes(request):
    reportes = ReporteIncidencia.objects.all()
    return render(request, "reportes/lista_reportes.html", {"reportes": reportes})

@login_required
def crear_reporte(request):
    if request.method == "POST":
        form = ReporteIncidenciaForm(request.POST)
        if form.is_valid():
            reporte = form.save(commit=False)
            reporte.usuario = request.user
            reporte.save()
            return redirect("lista_reportes")
    else:
        form = ReporteIncidenciaForm()
    return render(request, "reportes/crear_reporte.html", {"form": form})
