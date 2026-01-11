#!/usr/bin/env python
"""
Script para configurar niveles de stock por defecto en productos existentes
Este script debe ejecutarse desde la raíz del proyecto Django
"""

import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import ProductoTerminado

def configurar_stock_productos():
    """
    Configura niveles de stock por defecto para productos existentes
    """
    productos = ProductoTerminado.objects.all()
    
    print(f"Configurando niveles de stock para {productos.count()} productos...")
    
    productos_actualizados = 0
    
    for producto in productos:
        # Solo actualizar productos que no tienen configuración de stock
        if producto.stock_minimo == 0 and producto.stock_objetivo == 0:
            # Configurar niveles basados en el stock actual
            stock_actual = producto.stock
            
            if stock_actual > 0:
                # Stock mínimo: 20% del stock actual (mínimo 5 unidades)
                stock_minimo = max(5, int(stock_actual * 0.2))
                # Stock objetivo: 150% del stock actual
                stock_objetivo = int(stock_actual * 1.5)
            else:
                # Para productos sin stock, usar valores mínimos
                stock_minimo = 10
                stock_objetivo = 50
            
            # Actualizar el producto
            producto.stock_minimo = stock_minimo
            producto.stock_objetivo = stock_objetivo
            producto.produccion_habilitada = True
            producto.save()
            
            productos_actualizados += 1
            print(f"✓ {producto.descripcion}: Stock mínimo={stock_minimo}, Stock objetivo={stock_objetivo}")
    
    print(f"\n¡Configuración completada! {productos_actualizados} productos actualizados.")
    
    # Mostrar resumen de productos que necesitan reposición
    productos_criticos = ProductoTerminado.objects.filter(
        stock__lte=django.db.models.F('stock_minimo'),
        produccion_habilitada=True
    )
    
    if productos_criticos.exists():
        print(f"\n⚠️  ATENCIÓN: {productos_criticos.count()} productos necesitan reposición:")
        for producto in productos_criticos:
            print(f"   - {producto.descripcion}: Stock actual={producto.stock}, Stock mínimo={producto.stock_minimo}")
    else:
        print("\n✅ Todos los productos están dentro de los niveles normales de stock.")

if __name__ == "__main__":
    configurar_stock_productos()
