#!/usr/bin/env python3
"""
Script para probar la sincronización mejorada de estados entre OVs y OPs.
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

def probar_sincronizacion_estados():
    """
    Prueba la nueva lógica de sincronización de estados.
    """
    print("=== PROBANDO SINCRONIZACIÓN MEJORADA DE ESTADOS OV-OP ===\n")
    
    # Obtener todas las OVs con sus OPs
    ovs = OrdenVenta.objects.prefetch_related('ops_generadas__estado_op').all()
    
    if not ovs.exists():
        print("❌ No hay OVs para probar.")
        return
    
    print(f"📊 Encontradas {ovs.count()} OVs para analizar\n")
    
    for ov in ovs:
        print(f"🏷️  {ov.numero_ov} - Estado actual: {ov.get_estado_display()}")
        
        ops = ov.ops_generadas.all()
        if not ops.exists():
            print("   ⚠️  Sin OPs asociadas")
            print("   " + "="*50)
            continue
        
        # Mostrar estado actual de las OPs
        contador_estados = Counter()
        for op in ops:
            estado_nombre = op.estado_op.nombre if op.estado_op else "Sin estado"
            contador_estados[estado_nombre] += 1
        
        print("   📋 Estados de OPs asociadas:")
        for estado, cantidad in contador_estados.items():
            print(f"      • {cantidad} OP(s) en estado: {estado}")
        
        # Obtener resumen usando el nuevo método
        resumen = ov.get_resumen_estados_ops()
        print(f"   📈 Resumen: {resumen}")
        
        # Guardar estado anterior
        estado_anterior = ov.estado
        
        # Aplicar nueva lógica de sincronización
        print("   🔄 Aplicando nueva lógica de sincronización...")
        ov.actualizar_estado_por_ops()
        
        # Refrescar desde DB para ver cambios
        ov.refresh_from_db()
        
        if estado_anterior != ov.estado:
            print(f"   ✅ Estado actualizado: {estado_anterior} → {ov.get_estado_display()}")
        else:
            print(f"   ℹ️  Estado sin cambios: {ov.get_estado_display()}")
        
        print("   " + "="*50)
    
    print("\n=== RESUMEN DE ESTADOS DESPUÉS DE SINCRONIZACIÓN ===")
    
    # Mostrar resumen final por estado
    contador_final = Counter()
    for ov in OrdenVenta.objects.all():
        contador_final[ov.get_estado_display()] += 1
    
    for estado, cantidad in contador_final.most_common():
        print(f"📊 {cantidad} OV(s) en estado: {estado}")

def probar_casos_especiales():
    """
    Prueba casos especiales de estados mixtos.
    """
    print("\n=== PROBANDO CASOS ESPECIALES ===\n")
    
    # Buscar OVs con estados mixtos
    ovs_con_ops_multiples = OrdenVenta.objects.filter(
        ops_generadas__isnull=False
    ).prefetch_related('ops_generadas__estado_op').distinct()
    
    casos_mixtos = []
    
    for ov in ovs_con_ops_multiples:
        ops = ov.ops_generadas.all()
        if ops.count() > 1:
            estados_unicos = set()
            for op in ops:
                if op.estado_op:
                    estados_unicos.add(op.estado_op.nombre)
            
            if len(estados_unicos) > 1:
                casos_mixtos.append(ov)
    
    print(f"🔍 Encontradas {len(casos_mixtos)} OVs con estados mixtos en sus OPs:")
    
    for ov in casos_mixtos:
        print(f"\n🏷️  {ov.numero_ov}")
        ops = ov.ops_generadas.all()
        
        print("   📋 Detalle de OPs:")
        for op in ops:
            estado_nombre = op.estado_op.nombre if op.estado_op else "Sin estado"
            print(f"      • {op.numero_op}: {estado_nombre}")
        
        print(f"   📈 Estado actual OV: {ov.get_estado_display()}")
        print(f"   📝 Resumen de estados: {ov.get_resumen_estados_ops()}")

if __name__ == "__main__":
    try:
        probar_sincronizacion_estados()
        probar_casos_especiales()
        print("\n✅ Prueba completada exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()
