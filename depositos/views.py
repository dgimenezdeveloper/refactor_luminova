
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404
from .models import Deposito, StockProductoTerminado
from django.contrib.auth.models import Group

# Verifica si el usuario es admin (superuser o grupo Administradores)
def es_admin(user):
    return user.is_superuser or user.groups.filter(name="Administradores").exists()

@login_required
def deposito_stock_view(request, deposito_id):
    deposito = get_object_or_404(Deposito, id=deposito_id)
    # Si no es admin, solo puede ver su propio depósito (asumiendo que el usuario tiene un campo deposito)
    if not es_admin(request.user):
        if hasattr(request.user, "deposito"):
            if request.user.deposito.id != deposito.id:
                return render(request, "403.html", {"mensaje": "No tienes permiso para ver este depósito."})
        else:
            return render(request, "403.html", {"mensaje": "No tienes depósito asignado."})
    stocks = StockProductoTerminado.objects.filter(deposito=deposito)
    return render(request, "depositos/stock_por_deposito.html", {"deposito": deposito, "stocks": stocks})
