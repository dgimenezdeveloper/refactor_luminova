# Script para actualizar OCs viejas con precio_unitario_compra N/A usando la oferta más reciente
from App_LUMINOVA.models import Orden, OfertaProveedor
from django.db.models import Q

def run():
    ocs = Orden.objects.filter(Q(precio_unitario_compra__isnull=True) | Q(precio_unitario_compra=0))
    count = 0
    for oc in ocs:
        oferta = OfertaProveedor.objects.filter(insumo=oc.insumo_principal, proveedor=oc.proveedor).order_by('-fecha_actualizacion_precio').first()
        if oferta and oferta.precio_unitario_compra:
            oc.precio_unitario_compra = oferta.precio_unitario_compra
            oc.save(update_fields=['precio_unitario_compra'])
            count += 1
    print(f'Actualizadas {count} OCs con precio de oferta.')

if __name__ == "__main__":
    run()
