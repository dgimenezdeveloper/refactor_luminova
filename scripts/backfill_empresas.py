"""Script utilitario para popular el campo empresa en registros existentes."""
import os
import sys
from pathlib import Path

import django


BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Proyecto_LUMINOVA.settings")
django.setup()

from App_LUMINOVA import models  # noqa: E402  pylint: disable=wrong-import-position


SCOPED_MODELS = [
    models.CategoriaProductoTerminado,
    models.ProductoTerminado,
    models.CategoriaInsumo,
    models.Proveedor,
    models.Fabricante,
    models.Insumo,
    models.OfertaProveedor,
    models.ComponenteProducto,
    models.Cliente,
    models.OrdenVenta,
    models.ItemOrdenVenta,
    models.OrdenProduccion,
    models.Reportes,
    models.Factura,
    models.Orden,
    models.LoteProductoTerminado,
    models.HistorialOV,
    models.StockInsumo,
    models.StockProductoTerminado,
    models.MovimientoStock,
    models.NotificacionSistema,
]

EMPRESA_DEFAULT = None
default_empresa_id = os.getenv("DEFAULT_EMPRESA_ID")
if default_empresa_id:
    EMPRESA_DEFAULT = models.Empresa.objects.filter(id=default_empresa_id).first()
elif models.Empresa.objects.count() == 1:
    EMPRESA_DEFAULT = models.Empresa.objects.first()


def backfill_model(model_cls):
    """Actualiza registros sin empresa usando las reglas del mixin."""
    updated = 0
    pending_qs = model_cls.objects.filter(empresa__isnull=True)
    for obj in pending_qs.iterator():
        before = obj.empresa_id
        # ensure_empresa ya asigna usando relaciones conocidas
        obj.ensure_empresa()
        if not obj.empresa_id and EMPRESA_DEFAULT:
            obj.empresa = EMPRESA_DEFAULT
        if obj.empresa_id and obj.empresa_id != before:
            obj.save(update_fields=["empresa"])
            updated += 1
    return pending_qs.count(), updated


def run():
    total_pending = 0
    total_updated = 0
    for model_cls in SCOPED_MODELS:
        pending, updated = backfill_model(model_cls)
        total_pending += pending
        total_updated += updated
        print(f"{model_cls.__name__}: {updated}/{pending} registros actualizados")

    print("-" * 50)
    print(f"Total registros pendientes: {total_pending}")
    print(f"Total registros actualizados: {total_updated}")


if __name__ == "__main__":
    run()