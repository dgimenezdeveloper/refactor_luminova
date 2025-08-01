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