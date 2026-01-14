"""
Script de migración de datos para normalización de stock.
Este script debe ejecutarse ANTES de aplicar la migración 0036.

Objetivo: 
- Verificar que todos los Insumo y ProductoTerminado tienen su stock
  correctamente registrado en StockInsumo y StockProductoTerminado.
- Si hay datos en Insumo.stock o ProductoTerminado.stock que no están
  en las tablas normalizadas, los copia.

Uso:
    python manage.py shell < scripts/backfill_stock_normalizacion.py
    
O bien:
    python manage.py shell
    >>> exec(open('scripts/backfill_stock_normalizacion.py').read())
"""
import sys
import os

# Asegurarse de que Django está configurado
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')

import django
django.setup()

from django.db import transaction
from django.db.models import Sum

# Importar modelos
from App_LUMINOVA.models import (
    Insumo, ProductoTerminado, StockInsumo, StockProductoTerminado, Deposito
)


def backfill_stock_insumos():
    """
    Verifica y migra datos de Insumo.stock → StockInsumo
    """
    print("\n" + "="*60)
    print("BACKFILL DE STOCK PARA INSUMOS")
    print("="*60)
    
    insumos_migrados = 0
    insumos_ya_ok = 0
    errores = []
    
    # Obtener todos los insumos que tienen stock > 0 en el campo antiguo
    # O todos los insumos para verificar consistencia
    insumos = Insumo.objects.all().select_related('deposito', 'empresa')
    
    print(f"Total de insumos a verificar: {insumos.count()}")
    
    for insumo in insumos:
        try:
            # Obtener stock actual del campo antiguo (si existe)
            stock_antiguo = getattr(insumo, '_stock_field', 0)
            
            # Si el insumo no tiene depósito, no podemos crear StockInsumo
            if not insumo.deposito:
                if stock_antiguo > 0:
                    errores.append(f"Insumo '{insumo.descripcion}' (ID: {insumo.pk}) tiene stock={stock_antiguo} pero no tiene depósito asignado")
                continue
            
            # Verificar si ya existe registro en StockInsumo
            stock_record, created = StockInsumo.objects.get_or_create(
                insumo=insumo,
                deposito=insumo.deposito,
                defaults={
                    'cantidad': stock_antiguo if stock_antiguo > 0 else 0,
                    'empresa': insumo.empresa or insumo.deposito.empresa
                }
            )
            
            if created:
                insumos_migrados += 1
                print(f"  ✅ Creado StockInsumo para '{insumo.descripcion[:40]}...' - Cantidad: {stock_record.cantidad}")
            else:
                # Ya existía, verificar consistencia
                if stock_record.cantidad != stock_antiguo and stock_antiguo > 0:
                    print(f"  ⚠️  Inconsistencia en '{insumo.descripcion[:40]}...': StockInsumo={stock_record.cantidad}, campo antiguo={stock_antiguo}")
                else:
                    insumos_ya_ok += 1
                    
        except Exception as e:
            errores.append(f"Error procesando insumo '{insumo.descripcion}' (ID: {insumo.pk}): {str(e)}")
    
    # Resumen
    print("\n" + "-"*40)
    print("RESUMEN INSUMOS:")
    print(f"  - Migrados (nuevos StockInsumo): {insumos_migrados}")
    print(f"  - Ya correctos: {insumos_ya_ok}")
    print(f"  - Errores: {len(errores)}")
    
    if errores:
        print("\nERRORES:")
        for error in errores:
            print(f"  ❌ {error}")
    
    return insumos_migrados, insumos_ya_ok, errores


def backfill_stock_productos():
    """
    Verifica y migra datos de ProductoTerminado.stock → StockProductoTerminado
    """
    print("\n" + "="*60)
    print("BACKFILL DE STOCK PARA PRODUCTOS TERMINADOS")
    print("="*60)
    
    productos_migrados = 0
    productos_ya_ok = 0
    errores = []
    
    productos = ProductoTerminado.objects.all().select_related('deposito', 'empresa')
    
    print(f"Total de productos a verificar: {productos.count()}")
    
    for producto in productos:
        try:
            # Obtener stock actual del campo antiguo (si existe)
            stock_antiguo = getattr(producto, '_stock_field', 0)
            
            # Si el producto no tiene depósito, no podemos crear StockProductoTerminado
            if not producto.deposito:
                if stock_antiguo > 0:
                    errores.append(f"Producto '{producto.descripcion}' (ID: {producto.pk}) tiene stock={stock_antiguo} pero no tiene depósito asignado")
                continue
            
            # Verificar si ya existe registro en StockProductoTerminado
            stock_record, created = StockProductoTerminado.objects.get_or_create(
                producto=producto,
                deposito=producto.deposito,
                defaults={
                    'cantidad': stock_antiguo if stock_antiguo > 0 else 0,
                    'empresa': producto.empresa or producto.deposito.empresa
                }
            )
            
            if created:
                productos_migrados += 1
                print(f"  ✅ Creado StockProductoTerminado para '{producto.descripcion[:40]}...' - Cantidad: {stock_record.cantidad}")
            else:
                # Ya existía, verificar consistencia
                if stock_record.cantidad != stock_antiguo and stock_antiguo > 0:
                    print(f"  ⚠️  Inconsistencia en '{producto.descripcion[:40]}...': StockPT={stock_record.cantidad}, campo antiguo={stock_antiguo}")
                else:
                    productos_ya_ok += 1
                    
        except Exception as e:
            errores.append(f"Error procesando producto '{producto.descripcion}' (ID: {producto.pk}): {str(e)}")
    
    # Resumen
    print("\n" + "-"*40)
    print("RESUMEN PRODUCTOS:")
    print(f"  - Migrados (nuevos StockPT): {productos_migrados}")
    print(f"  - Ya correctos: {productos_ya_ok}")
    print(f"  - Errores: {len(errores)}")
    
    if errores:
        print("\nERRORES:")
        for error in errores:
            print(f"  ❌ {error}")
    
    return productos_migrados, productos_ya_ok, errores


def verificar_consistencia():
    """
    Verifica que no hay datos huérfanos o inconsistentes
    """
    print("\n" + "="*60)
    print("VERIFICACIÓN DE CONSISTENCIA")
    print("="*60)
    
    # Insumos sin depósito
    insumos_sin_deposito = Insumo.objects.filter(deposito__isnull=True).count()
    print(f"Insumos sin depósito: {insumos_sin_deposito}")
    
    # Productos sin depósito
    productos_sin_deposito = ProductoTerminado.objects.filter(deposito__isnull=True).count()
    print(f"Productos sin depósito: {productos_sin_deposito}")
    
    # StockInsumo huérfanos (sin insumo o depósito)
    stock_insumo_huerfano = StockInsumo.objects.filter(
        insumo__isnull=True
    ).count()
    print(f"StockInsumo huérfanos: {stock_insumo_huerfano}")
    
    # StockProductoTerminado huérfanos
    stock_producto_huerfano = StockProductoTerminado.objects.filter(
        producto__isnull=True
    ).count()
    print(f"StockProductoTerminado huérfanos: {stock_producto_huerfano}")
    
    # Verificar que cada insumo con depósito tiene su StockInsumo
    insumos_con_deposito = Insumo.objects.filter(deposito__isnull=False).count()
    stock_insumo_count = StockInsumo.objects.values('insumo', 'deposito').distinct().count()
    print(f"\nInsumos con depósito: {insumos_con_deposito}")
    print(f"Registros StockInsumo únicos: {stock_insumo_count}")
    
    # Verificar productos
    productos_con_deposito = ProductoTerminado.objects.filter(deposito__isnull=False).count()
    stock_producto_count = StockProductoTerminado.objects.values('producto', 'deposito').distinct().count()
    print(f"\nProductos con depósito: {productos_con_deposito}")
    print(f"Registros StockProductoTerminado únicos: {stock_producto_count}")
    
    return {
        'insumos_sin_deposito': insumos_sin_deposito,
        'productos_sin_deposito': productos_sin_deposito,
        'stock_insumo_huerfano': stock_insumo_huerfano,
        'stock_producto_huerfano': stock_producto_huerfano,
    }


def main():
    """
    Ejecuta el proceso completo de backfill y verificación
    """
    print("\n" + "="*80)
    print("INICIO DEL PROCESO DE BACKFILL DE STOCK")
    print("="*80)
    print("Este script verifica y migra datos de los campos stock antiguos")
    print("a las tablas normalizadas StockInsumo y StockProductoTerminado")
    
    # Verificación inicial
    stats_inicial = verificar_consistencia()
    
    # Ejecutar backfill en una transacción
    with transaction.atomic():
        insumos_stats = backfill_stock_insumos()
        productos_stats = backfill_stock_productos()
    
    # Verificación final
    print("\n" + "="*60)
    print("VERIFICACIÓN FINAL")
    print("="*60)
    stats_final = verificar_consistencia()
    
    # Resumen final
    print("\n" + "="*80)
    print("PROCESO COMPLETADO")
    print("="*80)
    print(f"Insumos migrados: {insumos_stats[0]}")
    print(f"Productos migrados: {productos_stats[0]}")
    print(f"Errores en insumos: {len(insumos_stats[2])}")
    print(f"Errores en productos: {len(productos_stats[2])}")
    
    if insumos_stats[2] or productos_stats[2]:
        print("\n⚠️  HAY ERRORES QUE REQUIEREN ATENCIÓN MANUAL")
        print("Revise los errores anteriores antes de aplicar la migración")
    else:
        print("\n✅ Todo OK. Puede proceder a aplicar la migración:")
        print("   python manage.py migrate")


if __name__ == "__main__":
    main()
else:
    # Si se ejecuta desde shell
    main()
