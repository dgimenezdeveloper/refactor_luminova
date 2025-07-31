from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q
from .models import MovimientoStock, Deposito, Insumo
from django.contrib.auth.models import User
from django.utils import timezone

@login_required
def historial_transferencias_view(request):
    depositos = Deposito.objects.all()
    usuarios = User.objects.all()
    insumos = Insumo.objects.all()
    transferencias = MovimientoStock.objects.filter(tipo="transferencia").select_related(
        "insumo", "deposito_origen", "deposito_destino", "usuario"
    ).order_by("-fecha")

    # Filtros
    deposito_origen_id = request.GET.get("deposito_origen")
    deposito_destino_id = request.GET.get("deposito_destino")
    usuario_id = request.GET.get("usuario")
    insumo_id = request.GET.get("insumo")
    fecha_desde = request.GET.get("fecha_desde")
    fecha_hasta = request.GET.get("fecha_hasta")

    if deposito_origen_id:
        transferencias = transferencias.filter(deposito_origen_id=deposito_origen_id)
    if deposito_destino_id:
        transferencias = transferencias.filter(deposito_destino_id=deposito_destino_id)
    if usuario_id:
        transferencias = transferencias.filter(usuario_id=usuario_id)
    if insumo_id:
        transferencias = transferencias.filter(insumo_id=insumo_id)
    if fecha_desde:
        transferencias = transferencias.filter(fecha__gte=fecha_desde)
    if fecha_hasta:
        transferencias = transferencias.filter(fecha__lte=fecha_hasta)

    context = {
        "transferencias": transferencias,
        "depositos": depositos,
        "usuarios": usuarios,
        "insumos": insumos,
        "filtros": {
            "deposito_origen_id": deposito_origen_id,
            "deposito_destino_id": deposito_destino_id,
            "usuario_id": usuario_id,
            "insumo_id": insumo_id,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        },
    }
    return render(request, "deposito/historial_transferencias.html", context)
