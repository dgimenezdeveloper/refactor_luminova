def es_admin(user):
    """Verifica si un usuario es superusuario o pertenece al grupo 'administrador'."""
    return user.groups.filter(name='administrador').exists() or user.is_superuser

def es_admin_o_rol(user, roles_permitidos=None):
    """Verifica si el usuario es superusuario, admin o pertenece a una lista de roles."""
    if user.is_superuser:
        return True
    if roles_permitidos is None:
        roles_permitidos = []
    # Normalizar nombres de roles
    roles_normalizados = []
    for rol in roles_permitidos:
        if rol.lower() == "deposito":
            roles_normalizados.append("Depósito")
        else:
            roles_normalizados.append(rol)
    if "administrador" not in roles_normalizados:
        roles_normalizados.append("administrador")
    return user.groups.filter(name__in=roles_normalizados).exists()

def redirigir_segun_rol(user):
    """Redirige al usuario a su módulo asignado según su rol principal."""
    from django.shortcuts import redirect
    from django.urls import reverse
    
    if user.is_superuser or user.groups.filter(name='administrador').exists():
        return redirect('App_LUMINOVA:dashboard')
    
    grupo_principal = user.groups.first()
    if not grupo_principal:
        return redirect('/')
    
    nombre_grupo = grupo_principal.name.lower()
    
    if nombre_grupo == 'compras':
        return redirect('App_LUMINOVA:compras_lista_oc')
    elif nombre_grupo == 'ventas':
        return redirect('App_LUMINOVA:ventas_lista_ov')
    elif nombre_grupo == 'produccion':
        return redirect('App_LUMINOVA:produccion_lista_op')
    elif nombre_grupo == 'control de calidad':
        return redirect('App_LUMINOVA:control_calidad_view')
    elif nombre_grupo == 'depósito':
        return redirect('App_LUMINOVA:seleccionar_deposito')
    else:
        return redirect('/')