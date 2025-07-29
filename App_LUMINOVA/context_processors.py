# TP_LUMINOVA-main/App_LUMINOVA/context_processors.py
from .models import Insumo, Orden, OrdenProduccion, Reportes


def notificaciones_context(request):
    if not request.user.is_authenticated:
        return {}


    deposito_id = request.session.get("deposito_seleccionado")

    # Notificaciones de OPs con problemas (no cambia, ya que depende de reportes, pero podría filtrarse por depósito si se requiere)
    ops_con_problemas_count = (
        Reportes.objects.filter(resuelto=False, orden_produccion_asociada__isnull=False)
        .values("orden_produccion_asociada_id")
        .distinct()
        .count()
    )

    # Solicitudes de insumos SOLO del depósito seleccionado
    if deposito_id:
        solicitudes_insumos_count = Orden.solicitudes_por_deposito(deposito_id).filter(
            estado_op__nombre__iexact="Insumos Solicitados"
        ).count()
        ocs_para_aprobar_count = Orden.pedidos_por_deposito(deposito_id).filter(
            tipo="compra", estado="BORRADOR"
        ).count()
        ocs_en_transito_count = Orden.pedidos_por_deposito(deposito_id).filter(
            tipo="compra", estado="EN_TRANSITO"
        ).count()
    else:
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
