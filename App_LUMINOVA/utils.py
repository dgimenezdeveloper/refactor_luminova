def es_admin(user):
    """
    Verifica si un usuario es superusuario o pertenece al grupo 'administrador'.
    Soporta formato multi-tenant: 'administrador' o 'ID__Administrador'
    """
    if user.is_superuser:
        return True
    # Buscar grupo administrador en cualquier formato
    for grupo in user.groups.all():
        nombre_lower = grupo.name.lower()
        # Formato directo o con prefijo de empresa (ej: '2__Administrador')
        if nombre_lower == 'administrador' or nombre_lower.endswith('__administrador'):
            return True
    return False


def tiene_rol(user, nombre_rol):
    """
    Verifica si el usuario tiene un rol específico.
    Soporta formato multi-tenant: 'rol' o 'ID__rol'
    
    Args:
        user: Usuario Django
        nombre_rol: Nombre del rol a verificar (case insensitive)
    
    Returns:
        bool: True si el usuario tiene el rol
    """
    nombre_rol_lower = nombre_rol.lower()
    # Normalizar variantes de depósito
    if nombre_rol_lower == "deposito":
        nombre_rol_lower = "depósito"
    
    for grupo in user.groups.all():
        nombre_grupo = grupo.name.lower()
        # Formato directo
        if nombre_grupo == nombre_rol_lower:
            return True
        # Formato multi-tenant (ej: '2__Depósito')
        if '__' in nombre_grupo:
            rol_sin_prefijo = nombre_grupo.split('__', 1)[1]
            if rol_sin_prefijo == nombre_rol_lower:
                return True
    return False


def es_admin_o_rol(user, roles_permitidos=None):
    """
    Verifica si el usuario es superusuario, admin o pertenece a una lista de roles.
    Soporta formato multi-tenant de grupos.
    """
    if user.is_superuser:
        return True
    if roles_permitidos is None:
        roles_permitidos = []
    
    # Normalizar nombres de roles permitidos
    roles_normalizados = set()
    for rol in roles_permitidos:
        rol_lower = rol.lower()
        if rol_lower == "deposito":
            roles_normalizados.add("depósito")
        roles_normalizados.add(rol_lower)
    
    # Siempre incluir administrador
    roles_normalizados.add("administrador")
    
    # Verificar si el usuario tiene alguno de los roles
    for grupo in user.groups.all():
        nombre_grupo = grupo.name.lower()
        # Verificar formato directo
        if nombre_grupo in roles_normalizados:
            return True
        # Verificar formato multi-tenant (ej: '2__ventas')
        if '__' in nombre_grupo:
            rol_sin_prefijo = nombre_grupo.split('__', 1)[1]
            if rol_sin_prefijo in roles_normalizados:
                return True
    return False


def redirigir_segun_rol(user):
    """Redirige al usuario a su modulo asignado segun su rol principal."""
    from django.shortcuts import redirect
    from django.urls import reverse
    
    # Si es admin, ir al dashboard
    if es_admin(user):
        return redirect('App_LUMINOVA:dashboard')
    
    grupo_principal = user.groups.first()
    if not grupo_principal:
        return redirect('/')
    
    # Obtener nombre del grupo sin prefijo de empresa
    nombre_grupo = grupo_principal.name.lower()
    if '__' in nombre_grupo:
        nombre_grupo = nombre_grupo.split('__', 1)[1]
    
    if nombre_grupo == 'compras':
        return redirect('App_LUMINOVA:compras_lista_oc')
    elif nombre_grupo == 'ventas':
        return redirect('App_LUMINOVA:ventas_lista_ov')
    elif nombre_grupo in ('produccion', 'producción'):
        return redirect('App_LUMINOVA:produccion_lista_op')
    elif nombre_grupo == 'control de calidad':
        return redirect('App_LUMINOVA:control_calidad_view')
    elif nombre_grupo in ('deposito', 'depósito'):
        return redirect('App_LUMINOVA:seleccionar_deposito')
    else:
        return redirect('/')