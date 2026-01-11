# App_LUMINOVA/views_empresas.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from .models import Empresa, PerfilUsuario, Deposito
from django.contrib.auth.models import User


def es_superusuario(user):
    return user.is_superuser


@login_required
def cambiar_empresa(request, empresa_id):
    """Vista para cambiar la empresa actual del usuario"""
    empresa = get_object_or_404(Empresa, id=empresa_id, activa=True)
    
    # Verificar permisos
    if not request.user.is_superuser:
        # Verificar que el usuario tenga acceso a esta empresa
        if not hasattr(request.user, 'perfil') or request.user.perfil.empresa != empresa:
            messages.error(request, "No tienes acceso a esta empresa.")
            return redirect('App_LUMINOVA:dashboard')
    
    # Cambiar empresa en la sesión
    request.session['empresa_actual_id'] = empresa.id
    messages.success(request, f"Empresa cambiada a: {empresa.nombre}")
    
    return redirect(request.META.get('HTTP_REFERER', 'App_LUMINOVA:dashboard'))


@login_required
@user_passes_test(es_superusuario)
def admin_empresas(request):
    """Vista de administración de empresas (solo superusuarios)"""
    empresas = Empresa.objects.all().order_by('-activa', 'nombre')
    
    context = {
        'empresas': empresas,
        'titulo_seccion': 'Administración de Empresas',
    }
    
    return render(request, 'admin/admin_empresas.html', context)


@login_required
@user_passes_test(es_superusuario)
def admin_crear_empresa(request):
    """Vista para crear nueva empresa"""
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        razon_social = request.POST.get('razon_social', '')
        cuit = request.POST.get('cuit', '')
        direccion = request.POST.get('direccion', '')
        telefono = request.POST.get('telefono', '')
        email = request.POST.get('email', '')
        
        if not nombre:
            messages.error(request, "El nombre de la empresa es obligatorio.")
            return redirect('App_LUMINOVA:admin_empresas')
        
        try:
            with transaction.atomic():
                empresa = Empresa.objects.create(
                    nombre=nombre,
                    razon_social=razon_social,
                    cuit=cuit,
                    direccion=direccion,
                    telefono=telefono,
                    email=email,
                    activa=True
                )
                messages.success(request, f"Empresa '{empresa.nombre}' creada exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al crear empresa: {str(e)}")
    
    return redirect('App_LUMINOVA:admin_empresas')


@login_required
@user_passes_test(es_superusuario)
def admin_editar_empresa(request, empresa_id):
    """Vista para editar empresa existente"""
    empresa = get_object_or_404(Empresa, id=empresa_id)
    
    if request.method == 'POST':
        empresa.nombre = request.POST.get('nombre', empresa.nombre)
        empresa.razon_social = request.POST.get('razon_social', empresa.razon_social)
        empresa.cuit = request.POST.get('cuit', empresa.cuit)
        empresa.direccion = request.POST.get('direccion', empresa.direccion)
        empresa.telefono = request.POST.get('telefono', empresa.telefono)
        empresa.email = request.POST.get('email', empresa.email)
        
        try:
            empresa.save()
            messages.success(request, f"Empresa '{empresa.nombre}' actualizada exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al actualizar empresa: {str(e)}")
    
    return redirect('App_LUMINOVA:admin_empresas')


@login_required
@user_passes_test(es_superusuario)
def admin_toggle_empresa(request, empresa_id):
    """Vista para activar/desactivar empresa"""
    empresa = get_object_or_404(Empresa, id=empresa_id)
    
    empresa.activa = not empresa.activa
    empresa.save()
    
    estado = "activada" if empresa.activa else "desactivada"
    messages.success(request, f"Empresa '{empresa.nombre}' {estado} exitosamente.")
    
    return redirect('App_LUMINOVA:admin_empresas')


@login_required
@user_passes_test(es_superusuario)
def admin_detalle_empresa(request, empresa_id):
    """Vista de detalle de empresa con depósitos y usuarios"""
    empresa = get_object_or_404(Empresa, id=empresa_id)
    depositos = Deposito.objects.filter(empresa=empresa)
    usuarios = PerfilUsuario.objects.filter(empresa=empresa).select_related('user')
    
    context = {
        'empresa': empresa,
        'depositos': depositos,
        'usuarios': usuarios,
        'titulo_seccion': f'Detalle de {empresa.nombre}',
    }
    
    return render(request, 'admin/admin_detalle_empresa.html', context)
