# TP_LUMINOVA-main/App_LUMINOVA/context_processors.py
"""
Context processors para LUMINOVA con soporte multi-tenancy.
Todos los queries deben filtrar por empresa del usuario actual.
"""
from .models import Insumo, Orden, OrdenProduccion, Reportes, UsuarioDeposito
from .utils import es_admin as es_admin_func, tiene_rol


def notificaciones_context(request):
    """
    Context processor para mostrar contadores de notificaciones en la UI.
    Filtra todos los datos por la empresa actual del usuario.
    """
    if not request.user.is_authenticated:
        return {}
    
    # Obtener empresa actual desde el middleware
    empresa_actual = getattr(request, 'empresa_actual', None)
    
    deposito_id = request.session.get("deposito_seleccionado")
    es_admin = es_admin_func(request.user)

    # Base querysets filtrados por empresa
    base_reportes = Reportes.objects.all()
    base_ops = OrdenProduccion.objects.all()
    base_ordenes = Orden.objects.all()
    base_insumos = Insumo.objects.all()
    
    if empresa_actual:
        base_reportes = base_reportes.filter(empresa=empresa_actual)
        base_ops = base_ops.filter(empresa=empresa_actual)
        base_ordenes = base_ordenes.filter(empresa=empresa_actual)
        base_insumos = base_insumos.filter(empresa=empresa_actual)

    # Notificaciones de OPs con problemas
    ops_con_problemas_count = (
        base_reportes.filter(resuelto=False, orden_produccion_asociada__isnull=False)
        .values("orden_produccion_asociada_id")
        .distinct()
        .count()
    )

    # Solicitudes de insumos SOLO del depósito seleccionado
    if deposito_id and deposito_id != "-1":  # Si no es "todos los depósitos"
        try:
            # Filtrar por depósito específico
            solicitudes_insumos_count = base_ops.filter(
                producto_a_producir__deposito_id=deposito_id,
                estado_op__nombre__iexact="Insumos Solicitados"
            ).count()
            ocs_para_aprobar_count = base_ordenes.filter(
                insumo_principal__deposito_id=deposito_id,
                tipo="compra", 
                estado="BORRADOR"
            ).count()
            ocs_en_transito_count = base_ordenes.filter(
                insumo_principal__deposito_id=deposito_id,
                tipo="compra", 
                estado="EN_TRANSITO"
            ).count()
        except (ValueError, TypeError):
            # Si deposito_id no es válido, usar totales de la empresa
            solicitudes_insumos_count = base_ops.filter(
                estado_op__nombre__iexact="Insumos Solicitados"
            ).count()
            ocs_para_aprobar_count = base_ordenes.filter(
                tipo="compra", estado="BORRADOR"
            ).count()
            ocs_en_transito_count = base_ordenes.filter(
                tipo="compra", estado="EN_TRANSITO"
            ).count()
    else:
        # Si no hay depósito seleccionado o es "todos", mostrar totales de la empresa
        solicitudes_insumos_count = base_ops.filter(
            estado_op__nombre__iexact="Insumos Solicitados"
        ).count()
        ocs_para_aprobar_count = base_ordenes.filter(
            tipo="compra", estado="BORRADOR"
        ).count()
        ocs_en_transito_count = base_ordenes.filter(
            tipo="compra", estado="EN_TRANSITO"
        ).count()

    UMBRAL_STOCK_BAJO = 15000
    ESTADOS_OC_EN_PROCESO = [
        "APROBADA",
        "ENVIADA_PROVEEDOR",
        "EN_TRANSITO",
        "RECIBIDA_PARCIAL",
        "RECIBIDA_TOTAL",
        "COMPLETADA",
    ]

    # Excluimos los insumos que ya tienen una OC "en firme" (de la misma empresa)
    insumos_con_oc_en_firme = base_ordenes.filter(
        tipo="compra", estado__in=ESTADOS_OC_EN_PROCESO
    ).values_list("insumo_principal_id", flat=True)

    # Filtrar insumos críticos por empresa
    insumos_criticos_qs = base_insumos.filter(
        stock__lt=UMBRAL_STOCK_BAJO
    ).exclude(id__in=insumos_con_oc_en_firme)
    insumos_stock_bajo_count = insumos_criticos_qs.count()

    total_notificaciones = (
        ops_con_problemas_count
        + solicitudes_insumos_count
        + ocs_para_aprobar_count
        + ocs_en_transito_count
        + insumos_stock_bajo_count
    )

    # Para los badges de sidebar, usar variables específicas
    # Badge de Recepción de Pedidos (sidebar): ocs_en_transito_count
    ocs_en_transito_count_sidebar = ocs_en_transito_count
    # Badge de Solicitudes de Insumos (sidebar): solicitudes_insumos_count
    solicitudes_insumos_count_sidebar = solicitudes_insumos_count

    return {
        "ops_con_problemas_count": ops_con_problemas_count,
        "solicitudes_insumos_count": solicitudes_insumos_count,
        "ocs_para_aprobar_count": ocs_para_aprobar_count,
        "ocs_en_transito_count": ocs_en_transito_count,
        "insumos_stock_bajo_count": insumos_stock_bajo_count,
        "total_notificaciones": total_notificaciones,
        # Para los badges de sidebar
        "ocs_en_transito_count_sidebar": ocs_en_transito_count_sidebar,
        "solicitudes_insumos_count_sidebar": solicitudes_insumos_count_sidebar,
    }

def puede_ver_deposito_sidebar(request):
    """
    Context processor para determinar si el usuario puede ver el sidebar de depósito.
    Filtra por empresa actual.
    Los administradores siempre tienen acceso al sidebar de depósito.
    """
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'puede_ver_deposito_sidebar': False}
    
    if user.is_superuser:
        return {'puede_ver_deposito_sidebar': True}
    
    # Los administradores de empresa tienen acceso completo al sidebar de depósito
    if es_admin_func(user):
        return {'puede_ver_deposito_sidebar': True}
    
    # Obtener empresa actual
    empresa_actual = getattr(request, 'empresa_actual', None)
    
    # Verificar si tiene depósitos asignados en la empresa actual
    usuario_depositos = UsuarioDeposito.objects.filter(usuario=user)
    if empresa_actual:
        usuario_depositos = usuario_depositos.filter(empresa=empresa_actual)
    
    tiene_depositos = usuario_depositos.exists()
    
    if tiene_rol(user, 'Depósito') and tiene_depositos:
        return {'puede_ver_deposito_sidebar': True}
    
    return {'puede_ver_deposito_sidebar': False}


def empresa_actual_context(request):
    """
    Context processor para agregar la empresa actual a todos los templates.
    """
    from .models import Empresa
    
    context = {
        'empresa_actual': None,
        'empresas_disponibles': [],
        'es_multi_empresa': False,
    }
    
    if request.user.is_authenticated:
        # Empresa actual desde el middleware
        context['empresa_actual'] = getattr(request, 'empresa_actual', None)
        
        # Si es superusuario, puede ver todas las empresas
        if request.user.is_superuser:
            empresas = Empresa.objects.filter(activa=True)
            context['empresas_disponibles'] = list(empresas)
            context['es_multi_empresa'] = empresas.count() > 1
        else:
            # Si tiene perfil, solo su empresa
            if hasattr(request.user, 'perfil'):
                context['empresas_disponibles'] = [request.user.perfil.empresa]
    
    return context
