import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')
import django
django.setup()

from django.db import connection
from productos.models import ProductoTerminado, CategoriaProductoTerminado
from depositos.models import Deposito, StockProductoTerminado

# 1. Migrar categorías de productos terminados
with connection.cursor() as cursor:
    cursor.execute('SELECT id, nombre, imagen FROM App_LUMINOVA_categoriaproductoterminado')
    categorias = cursor.fetchall()
    cat_map = {}
    for cat_id, nombre, imagen in categorias:
        cat_obj, _ = CategoriaProductoTerminado.objects.get_or_create(nombre=nombre, defaults={'imagen': imagen})
        cat_map[cat_id] = cat_obj

# 2. Migrar productos terminados
with connection.cursor() as cursor:
    cursor.execute('''SELECT id, descripcion, categoria_id, precio_unitario, modelo, potencia, acabado, color_luz, material, imagen FROM App_LUMINOVA_productoterminado''')
    productos = cursor.fetchall()
    prod_map = {}
    for (pid, descripcion, categoria_id, precio_unitario, modelo, potencia, acabado, color_luz, material, imagen) in productos:
        categoria = cat_map.get(categoria_id)
        prod_obj, _ = ProductoTerminado.objects.get_or_create(
            descripcion=descripcion,
            categoria=categoria,
            defaults={
                'precio_unitario': precio_unitario,
                'modelo': modelo,
                'potencia': potencia,
                'acabado': acabado,
                'color_luz': color_luz,
                'material': material,
                'imagen': imagen,
            }
        )
        prod_map[pid] = prod_obj

# 3. Migrar depósitos
with connection.cursor() as cursor:
    cursor.execute('SELECT id, nombre, ubicacion FROM App_LUMINOVA_deposito')
    depositos = cursor.fetchall()
    dep_map = {}
    for dep_id, nombre, ubicacion in depositos:
        dep_obj, _ = Deposito.objects.get_or_create(nombre=nombre, defaults={'ubicacion': ubicacion})
        dep_map[dep_id] = dep_obj

# 4. Migrar stocks de productos terminados por depósito
with connection.cursor() as cursor:
    cursor.execute('SELECT id, producto_id, deposito_id, cantidad FROM App_LUMINOVA_stockproductoterminado')
    stocks = cursor.fetchall()
    for sid, producto_id, deposito_id, cantidad in stocks:
        producto = prod_map.get(producto_id)
        deposito = dep_map.get(deposito_id)
        if producto and deposito:
            StockProductoTerminado.objects.get_or_create(producto=producto, deposito=deposito, defaults={'cantidad': cantidad})

print('Migración de productos terminados, categorías y stocks completada.')
