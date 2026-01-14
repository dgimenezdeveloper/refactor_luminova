"""
Vistas para importación masiva de datos
Sistema flexible adaptable a cualquier rubro empresarial
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.files.storage import default_storage
from django.conf import settings
from django.db.models import Sum, Count
import os
import logging

from .models import Empresa, Deposito, HistorialImportacion
from .services.importacion.insumo_importer import InsumoImporter
from .services.importacion.producto_importer import ProductoImporter
from .services.importacion.cliente_importer import ClienteImporter
from .services.importacion.proveedor_importer import ProveedorImporter

logger = logging.getLogger(__name__)


def guardar_historial(request, tipo, archivo_nombre, resultado, deposito=None):
    """Helper para guardar el historial de importación"""
    try:
        historial = HistorialImportacion.objects.create(
            empresa=request.empresa_actual,
            usuario=request.user,
            tipo_importacion=tipo,
            nombre_archivo=archivo_nombre,
            registros_importados=resultado.get('imported', 0),
            registros_actualizados=resultado.get('updated', 0),
            registros_con_error=len(resultado.get('errors', [])),
            exitoso=resultado.get('success', False),
            deposito=deposito,
            errores_detalle=resultado.get('errors', [])[:50],  # Limitar a 50 errores
            warnings_detalle=resultado.get('warnings', [])[:50],
        )
        return historial
    except Exception as e:
        logger.error(f"Error al guardar historial de importación: {str(e)}")
        return None


@login_required
def importacion_principal(request):
    """Vista principal del módulo de importación masiva"""
    empresa_actual = request.empresa_actual
    depositos = Deposito.objects.filter(empresa=empresa_actual) if empresa_actual else []
    
    # Obtener últimas importaciones para mostrar resumen
    ultimas_importaciones = []
    if empresa_actual:
        ultimas_importaciones = HistorialImportacion.objects.filter(
            empresa=empresa_actual
        ).select_related('usuario', 'deposito')[:5]
    
    context = {
        'empresa_actual': empresa_actual,
        'depositos': depositos,
        'tipos_importacion': [
            {'id': 'insumos', 'nombre': 'Insumos / Materias Primas', 'icon': 'bi-box-seam', 'color': 'primary'},
            {'id': 'productos', 'nombre': 'Productos Terminados', 'icon': 'bi-gift', 'color': 'success'},
            {'id': 'clientes', 'nombre': 'Clientes', 'icon': 'bi-people', 'color': 'info'},
            {'id': 'proveedores', 'nombre': 'Proveedores', 'icon': 'bi-truck', 'color': 'warning'},
        ],
        'ultimas_importaciones': ultimas_importaciones,
    }
    
    return render(request, 'importacion/importacion_principal.html', context)


@login_required
def importar_insumos(request):
    """Vista para importar insumos masivamente"""
    empresa_actual = request.empresa_actual
    depositos = Deposito.objects.filter(empresa=empresa_actual) if empresa_actual else []
    
    if request.method == 'POST':
        try:
            # Validar archivo
            if 'archivo' not in request.FILES:
                messages.error(request, "No se ha seleccionado ningún archivo")
                return render(request, 'importacion/importar_insumos.html', {
                    'empresa_actual': empresa_actual,
                    'depositos': depositos
                })
            
            archivo = request.FILES['archivo']
            actualizar_existentes = request.POST.get('actualizar_existentes') == 'on'
            deposito_id = request.POST.get('deposito')
            
            # Obtener depósito seleccionado o el primero
            if deposito_id:
                deposito = Deposito.objects.filter(id=deposito_id, empresa=empresa_actual).first()
            else:
                deposito = Deposito.objects.filter(empresa=empresa_actual).first()
            
            if not deposito:
                messages.error(request, "No hay depósitos configurados para esta empresa")
                return render(request, 'importacion/importar_insumos.html', {
                    'empresa_actual': empresa_actual,
                    'depositos': depositos
                })
            
            # Guardar archivo temporalmente
            file_extension = os.path.splitext(archivo.name)[1]
            temp_filename = f'temp_import_insumos_{request.user.id}{file_extension}'
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
            
            # Crear directorio temporal si no existe
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Guardar archivo
            with open(temp_path, 'wb+') as destination:
                for chunk in archivo.chunks():
                    destination.write(chunk)
            
            # Procesar importación
            importer = InsumoImporter(empresa=empresa_actual, deposito=deposito)
            resultado = importer.import_from_file(temp_path, update_existing=actualizar_existentes)
            
            # Eliminar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Guardar en historial
            guardar_historial(request, 'insumos', archivo.name, resultado, deposito)
            
            # Preparar contexto con resultados
            context = {
                'empresa_actual': empresa_actual,
                'depositos': depositos,
                'deposito_seleccionado': deposito.id,
                'resultado': {
                    'exitoso': resultado.get('success', False),
                    'importados': resultado.get('imported', 0),
                    'actualizados': resultado.get('updated', 0),
                    'errores': len(resultado.get('errors', [])),
                    'mensajes_error': resultado.get('errors', []),
                    'mensajes_warning': resultado.get('warnings', []),
                }
            }
            
            # Mensaje de éxito/error
            if resultado.get('success'):
                messages.success(request, f"Importación completada: {resultado.get('imported', 0)} insumos importados")
            else:
                messages.warning(request, f"Importación con advertencias: revise los errores")
            
            return render(request, 'importacion/importar_insumos.html', context)
            
        except Exception as e:
            logger.error(f"Error en importación de insumos: {str(e)}")
            messages.error(request, f"Error inesperado: {str(e)}")
            return render(request, 'importacion/importar_insumos.html', {
                'empresa_actual': empresa_actual,
                'depositos': depositos
            })
    
    # GET: Mostrar formulario
    context = {
        'empresa_actual': empresa_actual,
        'depositos': depositos,
    }
    
    return render(request, 'importacion/importar_insumos.html', context)


@login_required
def importar_productos(request):
    """Vista para importar productos terminados masivamente"""
    empresa_actual = request.empresa_actual
    depositos = Deposito.objects.filter(empresa=empresa_actual) if empresa_actual else []
    
    if request.method == 'POST':
        try:
            # Validar archivo
            if 'archivo' not in request.FILES:
                messages.error(request, "No se ha seleccionado ningún archivo")
                return render(request, 'importacion/importar_productos.html', {
                    'empresa_actual': empresa_actual,
                    'depositos': depositos
                })
            
            archivo = request.FILES['archivo']
            actualizar_existentes = request.POST.get('actualizar_existentes') == 'on'
            deposito_id = request.POST.get('deposito')
            
            # Obtener depósito seleccionado o el primero
            if deposito_id:
                deposito = Deposito.objects.filter(id=deposito_id, empresa=empresa_actual).first()
            else:
                deposito = Deposito.objects.filter(empresa=empresa_actual).first()
            
            if not deposito:
                messages.error(request, "No hay depósitos configurados para esta empresa")
                return render(request, 'importacion/importar_productos.html', {
                    'empresa_actual': empresa_actual,
                    'depositos': depositos
                })
            
            # Guardar archivo temporalmente
            file_extension = os.path.splitext(archivo.name)[1]
            temp_filename = f'temp_import_productos_{request.user.id}{file_extension}'
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
            
            # Crear directorio temporal
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Guardar archivo
            with open(temp_path, 'wb+') as destination:
                for chunk in archivo.chunks():
                    destination.write(chunk)
            
            # Procesar importación
            importer = ProductoImporter(empresa=empresa_actual, deposito=deposito)
            resultado = importer.import_from_file(temp_path, update_existing=actualizar_existentes)
            
            # Eliminar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Guardar en historial
            guardar_historial(request, 'productos', archivo.name, resultado, deposito)
            
            # Preparar contexto con resultados
            context = {
                'empresa_actual': empresa_actual,
                'depositos': depositos,
                'deposito_seleccionado': deposito.id,
                'resultado': {
                    'exitoso': resultado.get('success', False),
                    'importados': resultado.get('imported', 0),
                    'actualizados': resultado.get('updated', 0),
                    'errores': len(resultado.get('errors', [])),
                    'mensajes_error': resultado.get('errors', []),
                    'mensajes_warning': resultado.get('warnings', []),
                }
            }
            
            # Mensaje de éxito/error
            if resultado.get('success'):
                messages.success(request, f"Importación completada: {resultado.get('imported', 0)} productos importados")
            else:
                messages.warning(request, f"Importación con advertencias: revise los errores")
            
            return render(request, 'importacion/importar_productos.html', context)
            
        except Exception as e:
            logger.error(f"Error en importación de productos: {str(e)}")
            messages.error(request, f"Error inesperado: {str(e)}")
            return render(request, 'importacion/importar_productos.html', {
                'empresa_actual': empresa_actual,
                'depositos': depositos
            })
    
    # GET: Mostrar formulario
    context = {
        'empresa_actual': empresa_actual,
        'depositos': depositos,
    }
    
    return render(request, 'importacion/importar_productos.html', context)


@login_required
def historial_importaciones(request):
    """Vista para mostrar historial de importaciones"""
    empresa_actual = request.empresa_actual
    
    # Obtener historial filtrado por empresa
    historial = []
    estadisticas = None
    
    if empresa_actual:
        historial = HistorialImportacion.objects.filter(
            empresa=empresa_actual
        ).select_related('usuario', 'deposito').order_by('-fecha_importacion')[:50]
        
        # Calcular estadísticas
        stats = HistorialImportacion.objects.filter(empresa=empresa_actual).aggregate(
            total_importaciones=Count('id'),
            total_registros=Sum('registros_importados'),
            total_actualizados=Sum('registros_actualizados'),
            total_errores=Sum('registros_con_error'),
        )
        
        estadisticas = {
            'total_importaciones': stats['total_importaciones'] or 0,
            'total_registros': stats['total_registros'] or 0,
            'total_actualizados': stats['total_actualizados'] or 0,
            'total_errores': stats['total_errores'] or 0,
        }
    
    context = {
        'empresa_actual': empresa_actual,
        'historial': historial,
        'estadisticas': estadisticas,
    }
    
    return render(request, 'importacion/historial.html', context)


@login_required
def descargar_plantilla_insumos(request):
    """Descarga plantilla Excel para importar insumos"""
    import pandas as pd
    from io import BytesIO
    
    # Crear DataFrame con columnas ejemplo - adaptado al rubro
    data = {
        'descripcion': [
            'Harina de trigo 000', 
            'Aceite de girasol', 
            'Sal fina',
            'Tornillos 5cm',
            'Pintura blanca'
        ],
        'precio': [25.50, 18.75, 12.00, 0.50, 150.00],
        'stock': [100, 50, 200, 1000, 20],
        'stock_minimo': [20, 10, 30, 200, 5],
        'categoria': ['Harinas', 'Aceites', 'Condimentos', 'Ferretería', 'Pinturas'],
        'fabricante': ['Molino X', 'Aceitera Y', 'Sal Z', 'Tornillería SA', 'Pinturas ABC'],
        'unidad': ['kg', 'litro', 'kg', 'unidad', 'litro'],
        'codigo': ['HAR001', 'ACE001', 'SAL001', 'TOR001', 'PIN001']
    }
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel en memoria con formato mejorado
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Insumos')
        
        # Agregar hoja de instrucciones
        instrucciones = pd.DataFrame({
            'Campo': ['descripcion', 'precio', 'stock', 'stock_minimo', 'categoria', 'fabricante', 'unidad', 'codigo'],
            'Obligatorio': ['Sí', 'No', 'No', 'No', 'No', 'No', 'No', 'No'],
            'Descripción': [
                'Nombre del insumo (OBLIGATORIO)',
                'Precio unitario de compra',
                'Stock actual disponible',
                'Stock mínimo para alerta',
                'Categoría del insumo (se crea si no existe)',
                'Nombre del fabricante (se crea si no existe)',
                'Unidad de medida (kg, litro, unidad, etc.)',
                'Código interno o SKU'
            ],
            'Aliases aceptados': [
                'nombre, producto, item, artículo, material',
                'precio_unitario, costo, valor',
                'stock_actual, cantidad, existencia',
                'minimo, min_stock, punto_reorden',
                'categoría, tipo, grupo, familia',
                'proveedor, marca',
                'unidad_medida, um, presentacion',
                'código, sku, referencia, cod'
            ]
        })
        instrucciones.to_excel(writer, index=False, sheet_name='Instrucciones')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_insumos.xlsx'
    
    return response


@login_required
def descargar_plantilla_productos(request):
    """Descarga plantilla Excel para importar productos"""
    import pandas as pd
    from io import BytesIO
    
    # Crear DataFrame con columnas ejemplo
    data = {
        'descripcion': [
            'Pizza Muzzarella', 
            'Empanadas de carne x12', 
            'Mesa de Roble',
            'Silla Moderna',
            'Estantería 5 niveles'
        ],
        'precio': [450.00, 280.00, 85000.00, 25000.00, 45000.00],
        'stock': [0, 0, 5, 12, 3],
        'stock_minimo': [5, 10, 2, 5, 2],
        'stock_objetivo': [15, 30, 10, 20, 8],
        'categoria': ['Pizzas', 'Empanadas', 'Mesas', 'Sillas', 'Estanterías'],
        'modelo': ['PIZZA-MUZ', 'EMP-CARNE', 'MES-ROB-001', 'SIL-MOD-001', 'EST-5N-001'],
        'produccion_habilitada': ['si', 'si', 'si', 'si', 'no']
    }
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Productos')
        
        # Agregar hoja de instrucciones
        instrucciones = pd.DataFrame({
            'Campo': ['descripcion', 'precio', 'stock', 'stock_minimo', 'stock_objetivo', 'categoria', 'modelo', 'produccion_habilitada'],
            'Obligatorio': ['Sí', 'No', 'No', 'No', 'No', 'No', 'No', 'No'],
            'Descripción': [
                'Nombre del producto (OBLIGATORIO)',
                'Precio de venta',
                'Stock actual disponible',
                'Stock mínimo para alerta',
                'Stock objetivo para producción',
                'Categoría del producto (se crea si no existe)',
                'Código o modelo del producto',
                'Si se puede producir (si/no)'
            ],
            'Aliases aceptados': [
                'nombre, producto, item, artículo, plato, servicio',
                'precio_unitario, valor, pvp',
                'stock_actual, cantidad, existencia',
                'minimo, min_stock',
                'objetivo, stock_max',
                'categoría, tipo, grupo, familia',
                'codigo, referencia, sku',
                'produccion, fabricable, producible'
            ]
        })
        instrucciones.to_excel(writer, index=False, sheet_name='Instrucciones')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_productos.xlsx'
    
    return response


@login_required
def descargar_plantilla_clientes(request):
    """Descarga plantilla Excel para importar clientes"""
    import pandas as pd
    from io import BytesIO
    
    data = {
        'nombre': ['Cliente Ejemplo 1', 'Cliente Ejemplo 2', 'Empresa ABC'],
        'direccion': ['Calle 123', 'Av. Principal 456', 'Zona Industrial'],
        'telefono': ['1234567890', '0987654321', '1122334455'],
        'email': ['cliente1@email.com', 'cliente2@email.com', 'contacto@empresaabc.com']
    }
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clientes')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_clientes.xlsx'
    
    return response


@login_required
def descargar_plantilla_proveedores(request):
    """Descarga plantilla Excel para importar proveedores"""
    import pandas as pd
    from io import BytesIO
    
    data = {
        'nombre': ['Proveedor Ejemplo 1', 'Distribuidora XYZ', 'Mayorista ABC'],
        'contacto': ['Juan Pérez', 'María García', 'Carlos López'],
        'telefono': ['1234567890', '0987654321', '1122334455'],
        'email': ['ventas@proveedor1.com', 'contacto@xyz.com', 'ventas@abc.com']
    }
    
    df = pd.DataFrame(data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Proveedores')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_proveedores.xlsx'
    
    return response


@login_required
def importar_clientes(request):
    """Vista para importar clientes masivamente"""
    empresa_actual = request.empresa_actual
    
    if request.method == 'POST':
        try:
            # Validar archivo
            if 'archivo' not in request.FILES:
                messages.error(request, "No se ha seleccionado ningún archivo")
                return render(request, 'importacion/importar_clientes.html', {
                    'empresa_actual': empresa_actual
                })
            
            archivo = request.FILES['archivo']
            actualizar_existentes = request.POST.get('actualizar_existentes') == 'on'
            
            # Guardar archivo temporalmente
            file_extension = os.path.splitext(archivo.name)[1]
            temp_filename = f'temp_import_clientes_{request.user.id}{file_extension}'
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
            
            # Crear directorio temporal si no existe
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Guardar archivo
            with open(temp_path, 'wb+') as destination:
                for chunk in archivo.chunks():
                    destination.write(chunk)
            
            # Procesar importación
            importer = ClienteImporter(empresa=empresa_actual)
            resultado = importer.import_from_file(temp_path, update_existing=actualizar_existentes)
            
            # Eliminar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Guardar en historial
            guardar_historial(request, 'clientes', archivo.name, resultado)
            
            # Preparar contexto con resultados
            context = {
                'empresa_actual': empresa_actual,
                'resultado': {
                    'exitoso': resultado.get('success', False),
                    'importados': resultado.get('imported', 0),
                    'actualizados': resultado.get('updated', 0),
                    'errores': len(resultado.get('errors', [])),
                    'mensajes_error': resultado.get('errors', []),
                    'mensajes_warning': resultado.get('warnings', []),
                }
            }
            
            # Mensaje de éxito/error
            if resultado.get('success'):
                messages.success(request, f"Importación completada: {resultado.get('imported', 0)} clientes importados")
            else:
                messages.warning(request, f"Importación con advertencias: revise los errores")
            
            return render(request, 'importacion/importar_clientes.html', context)
            
        except Exception as e:
            logger.error(f"Error en importación de clientes: {str(e)}")
            messages.error(request, f"Error inesperado: {str(e)}")
            return render(request, 'importacion/importar_clientes.html', {
                'empresa_actual': empresa_actual
            })
    
    # GET: Mostrar formulario
    context = {
        'empresa_actual': empresa_actual,
    }
    
    return render(request, 'importacion/importar_clientes.html', context)


@login_required
def importar_proveedores(request):
    """Vista para importar proveedores masivamente"""
    empresa_actual = request.empresa_actual
    
    if request.method == 'POST':
        try:
            # Validar archivo
            if 'archivo' not in request.FILES:
                messages.error(request, "No se ha seleccionado ningún archivo")
                return render(request, 'importacion/importar_proveedores.html', {
                    'empresa_actual': empresa_actual
                })
            
            archivo = request.FILES['archivo']
            actualizar_existentes = request.POST.get('actualizar_existentes') == 'on'
            
            # Guardar archivo temporalmente
            file_extension = os.path.splitext(archivo.name)[1]
            temp_filename = f'temp_import_proveedores_{request.user.id}{file_extension}'
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', temp_filename)
            
            # Crear directorio temporal si no existe
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Guardar archivo
            with open(temp_path, 'wb+') as destination:
                for chunk in archivo.chunks():
                    destination.write(chunk)
            
            # Procesar importación
            importer = ProveedorImporter(empresa=empresa_actual)
            resultado = importer.import_from_file(temp_path, update_existing=actualizar_existentes)
            
            # Eliminar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
            # Guardar en historial
            guardar_historial(request, 'proveedores', archivo.name, resultado)
            
            # Preparar contexto con resultados
            context = {
                'empresa_actual': empresa_actual,
                'resultado': {
                    'exitoso': resultado.get('success', False),
                    'importados': resultado.get('imported', 0),
                    'actualizados': resultado.get('updated', 0),
                    'errores': len(resultado.get('errors', [])),
                    'mensajes_error': resultado.get('errors', []),
                    'mensajes_warning': resultado.get('warnings', []),
                }
            }
            
            # Mensaje de éxito/error
            if resultado.get('success'):
                messages.success(request, f"Importación completada: {resultado.get('imported', 0)} proveedores importados")
            else:
                messages.warning(request, f"Importación con advertencias: revise los errores")
            
            return render(request, 'importacion/importar_proveedores.html', context)
            
        except Exception as e:
            logger.error(f"Error en importación de proveedores: {str(e)}")
            messages.error(request, f"Error inesperado: {str(e)}")
            return render(request, 'importacion/importar_proveedores.html', {
                'empresa_actual': empresa_actual
            })
    
    # GET: Mostrar formulario
    context = {
        'empresa_actual': empresa_actual,
    }
    
    return render(request, 'importacion/importar_proveedores.html', context)
