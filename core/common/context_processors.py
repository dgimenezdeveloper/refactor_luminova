from productos.models import OrdenProduccion, Reportes
from insumos.models import Insumo, Orden

def notificaciones_context(request):
    if not request.user.is_authenticated:
        return {}

    ops_con_problemas_count = (
        Reportes.objects.filter(resuelto=False, orden_produccion_asociada__isnull=False)
        .values("orden_produccion_asociada_id")
        .distinct()
        .count()
    )

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
    ).values_list("insumos__id", flat=True)

    insumos_stock_bajo = (
        Insumo.objects.filter(stock__lt=UMBRAL_STOCK_BAJO)
        .exclude(id__in=insumos_con_oc_en_firme)
        .count()
    )

    return {
        "ops_con_problemas_count": ops_con_problemas_count,
        "solicitudes_insumos_count": solicitudes_insumos_count,
        "ocs_para_aprobar_count": ocs_para_aprobar_count,
        "ocs_en_transito_count": ocs_en_transito_count,
        "insumos_stock_bajo": insumos_stock_bajo,
    }
