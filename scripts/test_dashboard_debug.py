#!/usr/bin/env python
"""
Script para probar el dashboard de producción para stock
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import ProductoTerminado, Deposito
from App_LUMINOVA.forms import FiltroProductosStockForm
from django.contrib.auth.models import User
from django.db.models import F, Q

def test_dashboard_data():
    print("=== PRUEBA DASHBOARD PRODUCCIÓN PARA STOCK ===")
    
    # Obtener usuario y depósito
    usuario = User.objects.first()
    print(f"Usuario: {usuario}")
    
    # Obtener productos
    productos = ProductoTerminado.objects.select_related('categoria', 'deposito').all()
    print(f"Total productos en sistema: {productos.count()}")
    
    # Mostrar algunos productos para debug
    for producto in productos[:5]:
        print(f"- {producto.descripcion}")
        print(f"  Stock: {producto.stock}")
        print(f"  Stock mínimo: {producto.stock_minimo}")
        print(f"  Stock objetivo: {producto.stock_objetivo}")
        print(f"  Producción activa: {producto.produccion_para_stock_activa}")
        print(f"  Necesita reposición: {producto.necesita_reposicion_stock()}")
        print()
    
    # Probar filtros
    form_data = {'filtro': 'necesita_reposicion', 'buscar': ''}
    form = FiltroProductosStockForm(form_data)
    
    if form.is_valid():
        filtro = form.cleaned_data.get('filtro')
        print(f"Filtro aplicado: {filtro}")
        
        if filtro == 'necesita_reposicion':
            productos_filtrados = productos.filter(
                produccion_para_stock_activa=True,
                stock__lte=F('stock_minimo'),
                stock_minimo__gt=0
            )
            print(f"Productos que necesitan reposición: {productos_filtrados.count()}")
            
            for producto in productos_filtrados:
                print(f"- {producto.descripcion}: Stock {producto.stock}/{producto.stock_minimo}")
    
    # Verificar estadísticas
    productos_con_stock_bajo = productos.filter(
        stock__lte=F('stock_minimo'),
        stock_minimo__gt=0
    ).count()
    
    productos_necesitan_reposicion = productos.filter(
        produccion_para_stock_activa=True,
        stock__lte=F('stock_minimo'),
        stock_minimo__gt=0
    ).count()
    
    print(f"\nEstadísticas:")
    print(f"- Total productos: {productos.count()}")
    print(f"- Con stock bajo: {productos_con_stock_bajo}")
    print(f"- Necesitan reposición: {productos_necesitan_reposicion}")

if __name__ == '__main__':
    test_dashboard_data()
