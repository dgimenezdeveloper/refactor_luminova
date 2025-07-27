

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Movimiento
from .forms import MovimientoForm

@login_required
def lista_movimientos(request):
    movimientos = Movimiento.objects.all()
    return render(request, "movimientos/lista_movimientos.html", {"movimientos": movimientos})

@login_required
def crear_movimiento(request):
    if request.method == "POST":
        form = MovimientoForm(request.POST)
        if form.is_valid():
            movimiento = form.save(commit=False)
            movimiento.usuario = request.user
            movimiento.save()
            return redirect("lista_movimientos")
    else:
        form = MovimientoForm()
    return render(request, "movimientos/crear_movimiento.html", {"form": form})
