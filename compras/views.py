
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import OrdenCompra
from .forms import OrdenCompraForm

@login_required
def lista_compras(request):
    compras = OrdenCompra.objects.all()
    return render(request, "compras/lista_compras.html", {"compras": compras})

@login_required
def crear_compra(request):
    if request.method == "POST":
        form = OrdenCompraForm(request.POST)
        if form.is_valid():
            compra = form.save(commit=False)
            compra.usuario_solicitante = request.user
            compra.save()
            return redirect("lista_compras")
    else:
        form = OrdenCompraForm()
    return render(request, "compras/crear_compra.html", {"form": form})
