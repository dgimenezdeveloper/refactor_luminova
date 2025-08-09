#!/usr/bin/env python3
"""
Script para sincronizar los estados de las Órdenes de Venta (OV) 
basándose en el estado más avanzado de sus Órdenes de Producción (OP) asociadas.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import OrdenVenta, OrdenProduccion

def sincronizar_estados_ov():
    """
    Sincroniza los estados de todas las OV basándose en el estado más avanzado 
    de sus OPs asociadas.
    """
    # Mapeo de estados de OP a estados de OV y su prioridad
    MAPEO_ESTADOS_OP_A_OV = {
        "Completada": "COMPLETADA",
        "En Proceso": "PRODUCCION_INICIADA", 
        "Producción Iniciada": "PRODUCCION_INICIADA",
        "Insumos Recibidos": "INSUMOS_SOLICITADOS",
        "Insumos Solicitados": "INSUMOS_SOLICITADOS",
        "Planificada": "CONFIRMADA",
        "Pendiente": "PENDIENTE",
        "Cancelada": "CANCELADA",
    }
    
    ESTADOS_PRIORIDAD = {
        "COMPLETADA": 6,
        "LISTA_ENTREGA": 5,
        "PRODUCCION_INICIADA": 4,
        "INSUMOS_SOLICITADOS": 3,
        "CONFIRMADA": 2,
        "PENDIENTE": 1,
        "CANCELADA": 0,
    }

    # Obtener todas las OV
    ovs = OrdenVenta.objects.all()
    actualizadas = 0
    
    print(f"Procesando {ovs.count()} Órdenes de Venta...")
    
    for ov in ovs:
        # Obtener OPs asociadas a esta OV
        ops_asociadas = OrdenProduccion.objects.filter(orden_venta_origen=ov).select_related('estado_op')
        
        if not ops_asociadas.exists():
            print(f"OV {ov.numero_ov}: Sin OPs asociadas, mantiene estado {ov.estado}")
            continue
        
        # Obtener todos los estados de las OPs y mapearlos a estados de OV
        estados_ops = []
        for op in ops_asociadas:
            if op.estado_op and op.estado_op.nombre:
                estado_ov_mapeado = MAPEO_ESTADOS_OP_A_OV.get(op.estado_op.nombre)
                if estado_ov_mapeado:
                    estados_ops.append(estado_ov_mapeado)
                    print(f"  OP {op.numero_op}: {op.estado_op.nombre} -> {estado_ov_mapeado}")
        
        if not estados_ops:
            print(f"OV {ov.numero_ov}: Sin estados válidos para mapear")
            continue

        # Encontrar el estado más avanzado
        estado_mas_avanzado = max(
            estados_ops,
            key=lambda estado: ESTADOS_PRIORIDAD.get(estado, 0),
        )

        # Solo actualizar si el estado cambió
        if estado_mas_avanzado and estado_mas_avanzado != ov.estado:
            estado_anterior = ov.estado
            ov.estado = estado_mas_avanzado
            ov.save(update_fields=["estado"])
            actualizadas += 1
            print(f"OV {ov.numero_ov}: {estado_anterior} -> {estado_mas_avanzado}")
        else:
            print(f"OV {ov.numero_ov}: Estado {ov.estado} sin cambios")
    
    print(f"\nSincronización completada. {actualizadas} OV actualizadas.")

if __name__ == "__main__":
    sincronizar_estados_ov()
