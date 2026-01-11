#!/usr/bin/env python3
"""
Script para detectar y corregir inconsistencias en estados OV-OP.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import OrdenVenta, OrdenProduccion, EstadoOrden
from collections import Counter

def detectar_inconsistencias():
    """
    Detecta OVs con estados inconsistentes respecto a sus OPs.
    """
    print("=== DETECTANDO INCONSISTENCIAS EN ESTADOS ===\n")
    
    inconsistencias = []
    
    ovs = OrdenVenta.objects.prefetch_related('ops_generadas__estado_op').all()
    
    for ov in ovs:
        ops = ov.ops_generadas.all()
        if not ops.exists():
            continue
        
        # Contar estados de OPs
        contador_estados = Counter()
        for op in ops:
            if op.estado_op:
                contador_estados[op.estado_op.nombre] += 1
        
        total_ops = ops.count()
        ops_completadas = contador_estados.get("Completada", 0)
        ops_canceladas = contador_estados.get("Cancelada", 0)
        ops_activas = total_ops - ops_canceladas
        
        # Detectar inconsistencias
        problema = None
        
        # Caso 1: OV marcada como COMPLETADA pero tiene OPs no completadas
        if ov.estado == "COMPLETADA":
            if ops_completadas < ops_activas:
                ops_pendientes = [
                    f"{op.numero_op} ({op.estado_op.nombre})" 
                    for op in ops 
                    if op.estado_op and op.estado_op.nombre != "Completada" and op.estado_op.nombre != "Cancelada"
                ]
                problema = f"OV COMPLETADA con OPs pendientes: {', '.join(ops_pendientes)}"
        
        # Caso 2: Todas las OPs completadas pero OV no está en LISTA_ENTREGA o COMPLETADA
        elif ops_completadas == ops_activas and ops_activas > 0:
            if ov.estado not in ["LISTA_ENTREGA", "COMPLETADA"]:
                problema = f"Todas las OPs completadas pero OV en estado: {ov.get_estado_display()}"
        
        # Caso 3: Estados mixtos (algunas completadas, otras no)
        elif ops_completadas > 0 and ops_completadas < ops_activas:
            if ov.estado == "COMPLETADA":
                problema = f"Estado mixto: {ops_completadas}/{ops_activas} OPs completadas pero OV marcada como COMPLETADA"
        
        if problema:
            inconsistencias.append({
                'ov': ov,
                'problema': problema,
                'ops_completadas': ops_completadas,
                'ops_total': ops_activas,
                'detalle_ops': contador_estados
            })
    
    return inconsistencias

def mostrar_inconsistencias(inconsistencias):
    """
    Muestra las inconsistencias detectadas.
    """
    if not inconsistencias:
        print("✅ No se detectaron inconsistencias en los estados.")
        return
    
    print(f"🚨 Se detectaron {len(inconsistencias)} inconsistencias:\n")
    
    for i, inc in enumerate(inconsistencias, 1):
        ov = inc['ov']
        print(f"#{i} 🏷️  {ov.numero_ov} - Estado actual: {ov.get_estado_display()}")
        print(f"    📋 Problema: {inc['problema']}")
        print(f"    📊 OPs: {inc['ops_completadas']}/{inc['ops_total']} completadas")
        print(f"    📝 Detalle estados: {dict(inc['detalle_ops'])}")
        print("    " + "="*60)

def corregir_inconsistencias(inconsistencias, confirmar=True):
    """
    Corrige las inconsistencias detectadas.
    """
    if not inconsistencias:
        return
    
    print(f"\n=== CORRIGIENDO {len(inconsistencias)} INCONSISTENCIAS ===\n")
    
    correcciones_aplicadas = 0
    
    for inc in inconsistencias:
        ov = inc['ov']
        ops_completadas = inc['ops_completadas']
        ops_total = inc['ops_total']
        
        # Aplicar corrección usando la nueva lógica
        estado_anterior = ov.estado
        ov.actualizar_estado_por_ops()
        ov.refresh_from_db()
        
        if estado_anterior != ov.estado:
            print(f"✅ {ov.numero_ov}: {estado_anterior} → {ov.get_estado_display()}")
            correcciones_aplicadas += 1
        else:
            print(f"ℹ️  {ov.numero_ov}: Estado mantenido como {ov.get_estado_display()}")
    
    print(f"\n📊 Resumen: {correcciones_aplicadas} correcciones aplicadas")

def main():
    print("🔍 Detectando inconsistencias en estados OV-OP...\n")
    
    # Detectar inconsistencias
    inconsistencias = detectar_inconsistencias()
    
    # Mostrar resultados
    mostrar_inconsistencias(inconsistencias)
    
    # Corregir si hay inconsistencias
    if inconsistencias:
        print("\n🔧 Aplicando correcciones automáticas...")
        corregir_inconsistencias(inconsistencias)
        
        # Verificar después de correcciones
        print("\n🔍 Verificando después de correcciones...")
        inconsistencias_post = detectar_inconsistencias()
        
        if inconsistencias_post:
            print(f"⚠️  Quedan {len(inconsistencias_post)} inconsistencias sin resolver:")
            mostrar_inconsistencias(inconsistencias_post)
        else:
            print("✅ Todas las inconsistencias han sido resueltas!")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
