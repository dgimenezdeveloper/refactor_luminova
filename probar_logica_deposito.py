#!/usr/bin/env python
"""
Script para probar la lógica de la vista deposito_view
"""

from App_LUMINOVA.models import Insumo, Deposito, Orden
from django.db.models import Q

print("=== PRUEBA DE LÓGICA DE VISTA DEPOSITO ===")

# Simular la lógica de deposito_view
deposito = Deposito.objects.get(nombre="Depósito Central Luminova")
UMBRAL_STOCK_BAJO_INSUMOS = 15000

print(f"\nDepósito seleccionado: {deposito.nombre} (ID: {deposito.id})")

# Obtener insumos del depósito
insumos_del_deposito = Insumo.objects.filter(deposito=deposito)
print(f"Total insumos en depósito: {insumos_del_deposito.count()}")

# Filtrar insumos con stock bajo
insumos_con_stock_bajo = insumos_del_deposito.filter(stock__lt=UMBRAL_STOCK_BAJO_INSUMOS)
print(f"Insumos con stock < {UMBRAL_STOCK_BAJO_INSUMOS}: {insumos_con_stock_bajo.count()}")

# Estados que consideramos como "pedido en firme"
ESTADOS_OC_EN_PROCESO = [
    "APROBADA",
    "ENVIADA_PROVEEDOR", 
    "EN_TRANSITO",
    "RECIBIDA_PARCIAL",
]

print(f"\nDetalle de insumos con stock bajo:")
insumos_a_gestionar = []
insumos_en_pedido = []

for insumo in insumos_con_stock_bajo:
    print(f"- {insumo.descripcion} | Stock: {insumo.stock}")
    
    # Verificar si tiene OC en proceso
    oc_en_proceso = Orden.objects.filter(
        insumo_principal=insumo, 
        estado__in=ESTADOS_OC_EN_PROCESO
    ).order_by("-fecha_creacion").first()
    
    if oc_en_proceso:
        insumos_en_pedido.append({"insumo": insumo, "oc": oc_en_proceso})
        print(f"  → EN PEDIDO (OC: {oc_en_proceso.numero_orden})")
    else:
        insumos_a_gestionar.append(insumo)
        print(f"  → NECESITA GESTIÓN")

print(f"\nRESUMEN:")
print(f"- Insumos que necesitan gestión: {len(insumos_a_gestionar)}")
print(f"- Insumos ya en pedido: {len(insumos_en_pedido)}")

print(f"\nLISTA PARA TEMPLATE insumos_a_gestionar_list:")
for insumo in insumos_a_gestionar:
    print(f"  - {insumo.descripcion} (Stock: {insumo.stock})")

print(f"\nLISTA PARA TEMPLATE insumos_en_pedido_list:")
for item in insumos_en_pedido:
    print(f"  - {item['insumo'].descripcion} (OC: {item['oc'].numero_orden})")
