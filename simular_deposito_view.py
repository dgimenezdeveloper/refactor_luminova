#!/usr/bin/env python
"""
Script para simular exactamente la lógica de deposito_view
"""

from App_LUMINOVA.models import Insumo, Deposito, Orden, CategoriaInsumo, CategoriaProductoTerminado, OrdenProduccion, EstadoOrden, LoteProductoTerminado
from django.db.models import Q

print("=== SIMULACIÓN COMPLETA DE DEPOSITO_VIEW ===")

# Simular selección de depósito (normalmente viene de la sesión)
try:
    deposito = Deposito.objects.get(nombre="Depósito Central Luminova")
    print(f"\nDepósito simulado: {deposito.nombre} (ID: {deposito.id})")
except Deposito.DoesNotExist:
    print("Error: Depósito Central Luminova no encontrado")
    exit()

# 1. Obtener categorías del depósito
categorias_I = CategoriaInsumo.objects.filter(deposito=deposito)
categorias_PT = CategoriaProductoTerminado.objects.filter(deposito=deposito)

print(f"\nCategorías de Insumos: {categorias_I.count()}")
for cat in categorias_I[:3]:
    print(f"  - {cat.nombre}")

print(f"Categorías de Productos Terminados: {categorias_PT.count()}")
for cat in categorias_PT[:3]:
    print(f"  - {cat.nombre}")

# 2. OPs pendientes (necesita EstadoOrden)
ops_pendientes_deposito_count = 0
try:
    estado_sol = EstadoOrden.objects.filter(nombre__iexact="Insumos Solicitados").first()
    if estado_sol:
        ops_pendientes_deposito_list = OrdenProduccion.objects.filter(
            estado_op=estado_sol,
            producto_a_producir__deposito=deposito
        ).select_related("producto_a_producir").order_by("fecha_solicitud")
        ops_pendientes_deposito_count = ops_pendientes_deposito_list.count()
        print(f"\nOPs pendientes: {ops_pendientes_deposito_count}")
except Exception as e:
    print(f"\nError con OPs: {e}")

# 3. Lotes de productos terminados
try:
    lotes_en_stock = LoteProductoTerminado.objects.filter(
        enviado=False, 
        producto__deposito=deposito
    ).select_related("producto", "op_asociada").order_by("-fecha_creacion")
    print(f"\nLotes en stock: {lotes_en_stock.count()}")
except Exception as e:
    print(f"\nError con lotes: {e}")

# 4. LÓGICA PRINCIPAL - Insumos con stock bajo
UMBRAL_STOCK_BAJO_INSUMOS = 15000

# Filtro principal: insumos del depósito
insumos_del_deposito = Insumo.objects.filter(deposito=deposito)
print(f"\nTotal insumos en depósito: {insumos_del_deposito.count()}")

# Filtrar por stock bajo
insumos_con_stock_bajo = insumos_del_deposito.filter(stock__lt=UMBRAL_STOCK_BAJO_INSUMOS)
print(f"Insumos con stock < {UMBRAL_STOCK_BAJO_INSUMOS}: {insumos_con_stock_bajo.count()}")

# Estados de OC en proceso
ESTADOS_OC_EN_PROCESO = [
    "APROBADA",
    "ENVIADA_PROVEEDOR",
    "EN_TRANSITO", 
    "RECIBIDA_PARCIAL",
]

print(f"\nProcesando insumos con stock bajo:")
insumos_a_gestionar = []
insumos_en_pedido = []

for insumo in insumos_con_stock_bajo:
    print(f"\n  Procesando: {insumo.descripcion[:40]}... (Stock: {insumo.stock})")
    
    # Buscar OC en proceso
    oc_en_proceso = Orden.objects.filter(
        insumo_principal=insumo, 
        estado__in=ESTADOS_OC_EN_PROCESO
    ).order_by("-fecha_creacion").first()
    
    if oc_en_proceso:
        insumos_en_pedido.append({"insumo": insumo, "oc": oc_en_proceso, "stock_real": insumo.stock})
        print(f"    → EN PEDIDO (OC: {oc_en_proceso.numero_orden})")
    else:
        insumos_a_gestionar.append(insumo)
        print(f"    → NECESITA GESTIÓN")

print(f"\n=== RESULTADO FINAL ===")
print(f"insumos_a_gestionar_list: {len(insumos_a_gestionar)} elementos")
print(f"insumos_en_pedido_list: {len(insumos_en_pedido)} elementos")

print(f"\nINSUMOS QUE APARECERÁN EN LA TABLA 'Insumos con Stock Bajo':")
for i, insumo in enumerate(insumos_a_gestionar, 1):
    print(f"  {i}. {insumo.descripcion[:50]}... - Stock: {insumo.stock}")

print(f"\nINSUMOS QUE APARECERÁN EN LA TABLA 'Insumos en Pedido':")
for i, item in enumerate(insumos_en_pedido, 1):
    print(f"  {i}. {item['insumo'].descripcion[:50]}... - OC: {item['oc'].numero_orden}")

# Context que se envía al template
context = {
    "deposito": deposito,
    "categorias_I": categorias_I,
    "categorias_PT": categorias_PT,
    "ops_pendientes_deposito_count": ops_pendientes_deposito_count,
    "insumos_a_gestionar_list": insumos_a_gestionar,
    "insumos_en_pedido_list": insumos_en_pedido,
    "umbral_stock_bajo": UMBRAL_STOCK_BAJO_INSUMOS,
}

print(f"\n✅ Simulación completada. Context preparado para template.")
print(f"\nSi la tabla sigue vacía, el problema está en:")
print(f"1. La sesión del depósito no está configurada")
print(f"2. Los permisos del usuario")
print(f"3. El template no está recibiendo el context correctamente")
