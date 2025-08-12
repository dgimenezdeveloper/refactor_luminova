#!/usr/bin/env python3
"""
Script de prueba para verificar el funcionamiento de la funcionalidad de producción para stock.
Este script crea datos de prueba y verifica que el sistema funcione correctamente.
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from django.db import transaction
from App_LUMINOVA.models import (
    ProductoTerminado, OrdenProduccion, EstadoOrden, 
    CategoriaProductoTerminado, Deposito
)
from App_LUMINOVA.services.document_services import generar_siguiente_numero_documento


def crear_datos_prueba():
    """Crea datos de prueba para la funcionalidad de stock"""
    print("🔧 Creando datos de prueba...")
    
    with transaction.atomic():
        # Crear depósito de prueba si no existe
        deposito, created = Deposito.objects.get_or_create(
            nombre="Depósito Principal",
            defaults={
                'ubicacion': 'Planta Principal',
                'descripcion': 'Depósito principal para pruebas de stock'
            }
        )
        if created:
            print(f"  ✓ Depósito creado: {deposito.nombre}")
        
        # Crear categoría de prueba si no existe
        categoria, created = CategoriaProductoTerminado.objects.get_or_create(
            nombre="LED Prueba",
            deposito=deposito
        )
        if created:
            print(f"  ✓ Categoría creada: {categoria.nombre}")
        
        # Crear productos de prueba con diferentes configuraciones de stock
        productos_prueba = [
            {
                'descripcion': 'LED Panel 60x60 Prueba Stock',
                'modelo': 'LP6060-STOCK',
                'stock': 5,
                'stock_minimo': 10,
                'stock_objetivo': 25,
                'produccion_para_stock_activa': True,
                'precio_unitario': 150.00
            },
            {
                'descripcion': 'LED Downlight 12W Prueba',
                'modelo': 'LD12W-STOCK',
                'stock': 0,
                'stock_minimo': 15,
                'stock_objetivo': 30,
                'produccion_para_stock_activa': True,
                'precio_unitario': 75.00
            },
            {
                'descripcion': 'LED Strip 5m Prueba',
                'modelo': 'LS5M-NOSTOCK',
                'stock': 20,
                'stock_minimo': 5,
                'stock_objetivo': 15,
                'produccion_para_stock_activa': False,
                'precio_unitario': 45.00
            }
        ]
        
        productos_creados = []
        for producto_data in productos_prueba:
            producto, created = ProductoTerminado.objects.get_or_create(
                descripcion=producto_data['descripcion'],
                defaults={
                    'categoria': categoria,
                    'deposito': deposito,
                    **producto_data
                }
            )
            if created:
                print(f"  ✓ Producto creado: {producto.descripcion}")
                productos_creados.append(producto)
            else:
                # Actualizar el producto existente con los nuevos campos
                for key, value in producto_data.items():
                    if key != 'descripcion':
                        setattr(producto, key, value)
                producto.save()
                print(f"  ↻ Producto actualizado: {producto.descripcion}")
                productos_creados.append(producto)
        
        return productos_creados


def verificar_funcionalidad_stock():
    """Verifica que la funcionalidad de stock funcione correctamente"""
    print("\n🧪 Verificando funcionalidad de stock...")
    
    # Verificar productos que necesitan reposición
    productos_necesitan_reposicion = ProductoTerminado.objects.filter(
        produccion_para_stock_activa=True,
        stock__lte=django.db.models.F('stock_minimo'),
        stock_minimo__gt=0
    )
    
    print(f"  📊 Productos que necesitan reposición: {productos_necesitan_reposicion.count()}")
    
    for producto in productos_necesitan_reposicion:
        print(f"    - {producto.descripcion}: Stock {producto.stock} ≤ Mínimo {producto.stock_minimo}")
        print(f"      Cantidad sugerida para producir: {producto.cantidad_a_producir_para_stock()}")
    
    return productos_necesitan_reposicion


def crear_op_prueba():
    """Crea una OP de prueba para stock"""
    print("\n🏭 Creando OP de prueba para stock...")
    
    productos_necesitan_reposicion = ProductoTerminado.objects.filter(
        produccion_para_stock_activa=True,
        stock__lte=django.db.models.F('stock_minimo'),
        stock_minimo__gt=0
    ).first()
    
    if not productos_necesitan_reposicion:
        print("  ⚠️  No hay productos que necesiten reposición")
        return None
    
    try:
        with transaction.atomic():
            # Obtener estado inicial
            estado_inicial = EstadoOrden.objects.filter(nombre="Pendiente").first()
            if not estado_inicial:
                print("  ⚠️  No se encontró estado 'Pendiente', creando...")
                estado_inicial = EstadoOrden.objects.create(nombre="Pendiente")
            
            # Crear OP
            numero_op = generar_siguiente_numero_documento(OrdenProduccion, 'OP', 'numero_op')
            
            op = OrdenProduccion.objects.create(
                numero_op=numero_op,
                tipo_op="STOCK",
                producto_a_producir=productos_necesitan_reposicion,
                cantidad_a_producir=productos_necesitan_reposicion.cantidad_a_producir_para_stock(),
                estado_op=estado_inicial,
                notas="OP de prueba para verificar funcionalidad de stock"
            )
            
            print(f"  ✓ OP creada: {op.numero_op}")
            print(f"    Producto: {op.producto_a_producir.descripcion}")
            print(f"    Cantidad: {op.cantidad_a_producir}")
            print(f"    Tipo: {op.get_tipo_op_display()}")
            
            return op
            
    except Exception as e:
        print(f"  ❌ Error al crear OP: {str(e)}")
        return None


def verificar_metodos_modelo():
    """Verifica que los métodos del modelo funcionen correctamente"""
    print("\n🔍 Verificando métodos del modelo...")
    
    # Probar métodos de ProductoTerminado
    productos = ProductoTerminado.objects.all()[:3]
    
    for producto in productos:
        print(f"\n  Producto: {producto.descripcion}")
        print(f"    Stock actual: {producto.stock}")
        print(f"    Stock mínimo: {producto.stock_minimo}")
        print(f"    Stock objetivo: {producto.stock_objetivo}")
        print(f"    Producción activa: {producto.produccion_para_stock_activa}")
        print(f"    Necesita reposición: {producto.necesita_reposicion_stock()}")
        print(f"    Cantidad a producir: {producto.cantidad_a_producir_para_stock()}")
    
    # Probar métodos de OrdenProduccion
    ops = OrdenProduccion.objects.all()[:3]
    
    for op in ops:
        print(f"\n  OP: {op.numero_op}")
        print(f"    Tipo: {op.get_tipo_op_display()}")
        print(f"    Es para stock: {op.is_para_stock()}")
        print(f"    Es para demanda: {op.is_para_demanda()}")
        print(f"    Estado: {op.get_estado_op_display()}")


def main():
    """Función principal del script de prueba"""
    print("🚀 Iniciando pruebas de funcionalidad Producción para Stock")
    print("=" * 60)
    
    try:
        # Crear datos de prueba
        productos_creados = crear_datos_prueba()
        
        # Verificar funcionalidad
        productos_necesitan_reposicion = verificar_funcionalidad_stock()
        
        # Crear OP de prueba
        op_creada = crear_op_prueba()
        
        # Verificar métodos
        verificar_metodos_modelo()
        
        print("\n" + "=" * 60)
        print("✅ Todas las pruebas completadas exitosamente!")
        print(f"📦 Productos creados/actualizados: {len(productos_creados)}")
        print(f"⚠️  Productos que necesitan reposición: {productos_necesitan_reposicion.count()}")
        print(f"🏭 OP de prueba creada: {'Sí' if op_creada else 'No'}")
        
        if op_creada:
            print(f"\n🔗 Puedes ver la OP creada en:")
            print(f"   Admin: /admin/App_LUMINOVA/ordenproduccion/{op_creada.id}/change/")
            print(f"   Dashboard: /produccion/stock/dashboard/")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
