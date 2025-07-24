from django.shortcuts import render, redirect
from .models import Deposito

def deposito_selector_view(request):
    depositos = Deposito.objects.all()
    if request.method == "GET" and "deposito_id" in request.GET:
        deposito_id = request.GET.get("deposito_id")
        if deposito_id:
            return redirect('App_LUMINOVA:deposito_view') + f'?deposito_id={deposito_id}'
    return render(request, "deposito/deposito_selector.html", {"depositos": depositos})
