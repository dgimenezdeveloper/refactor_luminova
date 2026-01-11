#!/usr/bin/env python
"""
Script para debuggar exactamente lo que pasa en la vista del dashboard
"""
import os
import sys
import django

# Configurar Django
sys.path.append('/home/daseg/Documentos/mis_proyectos/TP_LUMINOVA-main')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
django.setup()

from App_LUMINOVA.models import ProductoTerminado, OrdenProduccion
from App_LUMINOVA.forms import FiltroProductosStockForm
from django.contrib.auth.models import User
from django.db.models import F, Q, Count, Sum
from App_LUMINOVA.utils import obtener_deposito_usuario

def debug_vista_completa():
    print("=== DEBUG COMPLETO DE LA VISTA ===")
    
    # Simular request GET con filtros
    filtro_data = {'filtro': 'necesita_reposicion', 'buscar': ''}
    form = FiltroProductosStockForm(filtro_data)
    
    print(f"Formulario válido: {form.is_valid()}")
    print(f"Datos del formulario: {form.cleaned_data if form.is_valid() else form.errors}")
    
    # Obtener usuario (simulando request.user)
    user = User.objects.first()
    deposito_user = obtener_deposito_usuario(user)
    print(f"Usuario: {user}")
    print(f"Depósito del usuario: {deposito_user}")
    
    # Obtener productos inicial
    productos = ProductoTerminado.objects.select_related('categoria', 'deposito').all()
    print(f"Productos iniciales: {productos.count()}")
    
    if deposito_user:
        productos = productos.filter(deposito=deposito_user)
        print(f"Productos después de filtrar por depósito: {productos.count()}")
    
    # Aplicar filtros del formulario
    if form.is_valid():
        filtro = form.cleaned_data.get('filtro')
        buscar = form.cleaned_data.get('buscar')
        
        print(f"Aplicando filtro: {filtro}")
        print(f"Aplicando búsqueda: {buscar}")
        
        if buscar:
            productos = productos.filter(
                Q(descripcion__icontains=buscar) |
                Q(modelo__icontains=buscar)
            )
            print(f"Productos después de búsqueda: {productos.count()}")
        
        if filtro == 'necesita_reposicion':
            print("Aplicando filtro 'necesita_reposicion'...")
            productos_antes = productos.count()
            productos = productos.filter(
                produccion_para_stock_activa=True,
                stock__lte=F('stock_minimo'),
                stock_minimo__gt=0
            )
            print(f"Productos antes del filtro: {productos_antes}")
            print(f"Productos después del filtro: {productos.count()}")
            
            # Mostrar productos específicos
            for producto in productos:
                print(f"  - {producto.descripcion}: stock={producto.stock}, min={producto.stock_minimo}, activa={producto.produccion_para_stock_activa}")
    
    # Verificar el contexto final
    productos_final = productos[:50]  # Limitar para performance
    print(f"\nProductos en contexto final: {len(productos_final)}")
    print(f"¿Lista vacía?: {len(productos_final) == 0}")
    print(f"¿Evaluaría a False?: {not productos_final}")
    
    # Verificar template condition
    if productos_final:
        print("✅ Template mostraría la tabla")
    else:
        print("❌ Template NO mostraría la tabla (condición {% if productos %} es False)")

if __name__ == '__main__':
    debug_vista_completa()
