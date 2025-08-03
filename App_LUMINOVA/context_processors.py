# TP_LUMINOVA-main/App_LUMINOVA/context_processors.py
from .models import Insumo, Orden, OrdenProduccion, Reportes, UsuarioDeposito


def notificaciones_context(request):
    if not request.user.is_authenticated:
        return {}


    deposito_id = request.session.get("deposito_seleccionado")
    es_admin = request.user.is_superuser or request.user.groups.filter(name='administrador').exists()

    # Notificaciones de OPs con problemas (no cambia, ya que depende de reportes, pero podría filtrarse por depósito si se requiere)
    ops_con_problemas_count = (
        Reportes.objects.filter(resuelto=False, orden_produccion_asociada__isnull=False)
        .values("orden_produccion_asociada_id")
        .distinct()
        .count()
    )

    # Solicitudes de insumos SOLO del depósito seleccionado
    if deposito_id and deposito_id != "-1":  # Si no es "todos los depósitos"
        try:
            solicitudes_insumos_count = Orden.solicitudes_por_deposito(deposito_id).filter(
                estado_op__nombre__iexact="Insumos Solicitados"
            ).count()
            ocs_para_aprobar_count = Orden.pedidos_por_deposito(deposito_id).filter(
                tipo="compra", estado="BORRADOR"
            ).count()
            ocs_en_transito_count = Orden.pedidos_por_deposito(deposito_id).filter(
                tipo="compra", estado="EN_TRANSITO"
            ).count()
        except (ValueError, TypeError):
            # Si deposito_id no es válido, usar totales globales
            solicitudes_insumos_count = OrdenProduccion.objects.filter(
                estado_op__nombre__iexact="Insumos Solicitados"
            ).count()
            ocs_para_aprobar_count = Orden.objects.filter(
                tipo="compra", estado="BORRADOR"
            ).count()
            ocs_en_transito_count = Orden.objects.filter(
                tipo="compra", estado="EN_TRANSITO"
            ).count()
    else:
        # Si no hay depósito seleccionado o es "todos", mostrar totales globales
        solicitudes_insumos_count = OrdenProduccion.objects.filter(
            estado_op__nombre__iexact="Insumos Solicitados"
        ).count()
        ocs_para_aprobar_count = Orden.objects.filter(
            tipo="compra", estado="BORRADOR"
        ).count()
        ocs_en_transito_count = Orden.objects.filter(
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

    # Excluimos los insumos que ya tienen una OC "en firme"
    insumos_con_oc_en_firme = Orden.objects.filter(
        tipo="compra", estado__in=ESTADOS_OC_EN_PROCESO
    ).values_list("insumo_principal_id", flat=True)

    insumos_stock_bajo_count = (
        Insumo.objects.filter(stock__lt=UMBRAL_STOCK_BAJO)
        .exclude(id__in=insumos_con_oc_en_firme)
        .count()
    )

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
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'puede_ver_deposito_sidebar': False}
    if user.is_superuser:
        return {'puede_ver_deposito_sidebar': True}
    tiene_depositos = UsuarioDeposito.objects.filter(usuario=user).exists()
    if user.groups.filter(name='Depósito').exists() and tiene_depositos:
        return {'puede_ver_deposito_sidebar': True}
    return {'puede_ver_deposito_sidebar': False}
