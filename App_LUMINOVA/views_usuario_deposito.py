from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User
from .models import Deposito, UsuarioDeposito
from .utils import es_admin, tiene_rol


@login_required
@user_passes_test(es_admin)
def gestionar_permisos_deposito_view(request, usuario_id):
    """Vista para gestionar permisos específicos de un usuario en depósitos"""
    usuario = get_object_or_404(User, id=usuario_id)
    
    # Verificar que el usuario tenga rol de depósito
    if not tiene_rol(usuario, 'Depósito'):
        messages.error(request, "Este usuario no tiene rol de depósito.")
        return redirect("App_LUMINOVA:lista_usuarios")
    
    # Obtener todas las asignaciones del usuario
    asignaciones = UsuarioDeposito.objects.filter(usuario=usuario).select_related('deposito')
    depositos_asignados_ids = {asig.deposito.id for asig in asignaciones}
    
    # Obtener todos los depósitos con información de asignación
    todos_depositos = []
    for deposito in Deposito.objects.all().order_by('nombre'):
        asignacion = next((asig for asig in asignaciones if asig.deposito.id == deposito.id), None)
        todos_depositos.append({
            'deposito': deposito,
            'asignacion': asignacion,
            'tiene_acceso': asignacion is not None,
        })
    
    context = {
        'usuario': usuario,
        'todos_depositos': todos_depositos,
        'titulo_seccion': f'Permisos de Depósito - {usuario.username}'
    }
    
    return render(request, 'admin/gestionar_permisos_deposito.html', context)


@login_required
@user_passes_test(es_admin)
@transaction.atomic
@require_POST
def actualizar_permisos_deposito_ajax(request):
    """Vista AJAX para actualizar permisos de usuario en depósitos"""
    try:
        usuario_id = request.POST.get('usuario_id')
        deposito_id = request.POST.get('deposito_id')
        puede_transferir = request.POST.get('puede_transferir') == 'true'
        puede_entradas = request.POST.get('puede_entradas') == 'true'
        puede_salidas = request.POST.get('puede_salidas') == 'true'
        tiene_acceso = request.POST.get('tiene_acceso') == 'true'
        
        usuario = get_object_or_404(User, id=usuario_id)
        deposito = get_object_or_404(Deposito, id=deposito_id)
        
        if tiene_acceso:
            # Crear o actualizar asignación
            asignacion, created = UsuarioDeposito.objects.get_or_create(
                usuario=usuario,
                deposito=deposito,
                defaults={
                    'puede_transferir': puede_transferir,
                    'puede_entradas': puede_entradas,
                    'puede_salidas': puede_salidas,
                }
            )
            
            if not created:
                # Actualizar permisos existentes
                asignacion.puede_transferir = puede_transferir
                asignacion.puede_entradas = puede_entradas
                asignacion.puede_salidas = puede_salidas
                asignacion.save()
                
            return JsonResponse({
                'success': True,
                'message': f'Permisos actualizados para {deposito.nombre}',
                'action': 'updated' if not created else 'created'
            })
        else:
            # Eliminar asignación si existe
            UsuarioDeposito.objects.filter(usuario=usuario, deposito=deposito).delete()
            return JsonResponse({
                'success': True,
                'message': f'Acceso removido para {deposito.nombre}',
                'action': 'deleted'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@user_passes_test(es_admin)
def usuarios_deposito_view(request):
    """Vista para gestionar asignaciones masivas de usuarios a depósitos"""
    usuarios_deposito = User.objects.filter(
        groups__name='Depósito'
    ).prefetch_related('depositos_asignados', 'depositos_asignados__deposito')
    
    depositos = Deposito.objects.all().order_by('nombre')
    
    context = {
        'usuarios_deposito': usuarios_deposito,
        'depositos': depositos,
        'titulo_seccion': 'Gestión Usuario-Depósito'
    }
    
    return render(request, 'admin/usuarios_deposito.html', context)
