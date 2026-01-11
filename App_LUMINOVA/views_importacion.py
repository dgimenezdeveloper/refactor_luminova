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
import os
import logging

from .models import Empresa, Deposito
from .services.importacion.insumo_importer import InsumoImporter
from .services.importacion.producto_importer import ProductoImporter

logger = logging.getLogger(__name__)


@login_required
def importacion_principal(request):
    """Vista principal del módulo de importación masiva"""
    empresa_actual = request.empresa_actual
    depositos = Deposito.objects.filter(empresa=empresa_actual) if empresa_actual else []
    
    context = {
        'empresa_actual': empresa_actual,
        'depositos': depositos,
        'tipos_importacion': [
            {'id': 'insumos', 'nombre': 'Insumos / Materias Primas', 'icon': 'bi-box-seam'},
            {'id': 'productos', 'nombre': 'Productos Terminados', 'icon': 'bi-basket'},
        ]
    }
    
    return render(request, 'importacion/importacion_principal.html', context)


@login_required
def importar_insumos(request):
    """Vista para importar insumos masivamente"""
    empresa_actual = request.empresa_actual
    
    if request.method == 'POST':
        try:
            # Validar archivo
            if 'archivo' not in request.FILES:
                messages.error(request, "No se ha seleccionado ningún archivo")
                return render(request, 'importacion/importar_insumos.html', {'empresa_actual': empresa_actual})
            
            archivo = request.FILES['archivo']
            actualizar_existentes = request.POST.get('actualizar_existentes') == 'on'
            
            # Obtener primer depósito de la empresa (por ahora simplificado)
            deposito = Deposito.objects.filter(empresa=empresa_actual).first()
            
            if not deposito:
                messages.error(request, "No hay depósitos configurados para esta empresa")
                return render(request, 'importacion/importar_insumos.html', {'empresa_actual': empresa_actual})
            
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
            resultado = importer.import_file(temp_path)
            
            # Eliminar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
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
            
            return render(request, 'importacion/importar_insumos.html', context)
            
        except Exception as e:
            logger.error(f"Error en importación de insumos: {str(e)}")
            messages.error(request, f"Error inesperado: {str(e)}")
            return render(request, 'importacion/importar_insumos.html', {'empresa_actual': empresa_actual})
    
    # GET: Mostrar formulario
    context = {
        'empresa_actual': empresa_actual,
    }
    
    return render(request, 'importacion/importar_insumos.html', context)


@login_required
def importar_productos(request):
    """Vista para importar productos terminados masivamente"""
    empresa_actual = request.empresa_actual
    
    if request.method == 'POST':
        try:
            # Validar archivo
            if 'archivo' not in request.FILES:
                messages.error(request, "No se ha seleccionado ningún archivo")
                return render(request, 'importacion/importar_productos.html', {'empresa_actual': empresa_actual})
            
            archivo = request.FILES['archivo']
            actualizar_existentes = request.POST.get('actualizar_existentes') == 'on'
            
            # Obtener primer depósito de la empresa
            deposito = Deposito.objects.filter(empresa=empresa_actual).first()
            
            if not deposito:
                messages.error(request, "No hay depósitos configurados para esta empresa")
                return render(request, 'importacion/importar_productos.html', {'empresa_actual': empresa_actual})
            
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
            resultado = importer.import_file(temp_path)
            
            # Eliminar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
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
            
            return render(request, 'importacion/importar_productos.html', context)
            
        except Exception as e:
            logger.error(f"Error en importación de productos: {str(e)}")
            messages.error(request, f"Error inesperado: {str(e)}")
            return render(request, 'importacion/importar_productos.html', {'empresa_actual': empresa_actual})
    
    # GET: Mostrar formulario
    context = {
        'empresa_actual': empresa_actual,
    }
    
    return render(request, 'importacion/importar_productos.html', context)


@login_required
def historial_importaciones(request):
    """Vista para mostrar historial de importaciones (placeholder por ahora)"""
    context = {
        'empresa_actual': request.empresa_actual,
        'historial': []  # TODO: implementar modelo de historial si es necesario
    }
    return render(request, 'importacion/historial.html', context)


@login_required
def descargar_plantilla_insumos(request):
    """Descarga plantilla Excel para importar insumos"""
    import pandas as pd
    from io import BytesIO
    
    # Crear DataFrame con columnas ejemplo
    data = {
        'descripcion': ['Harina de trigo 000', 'Aceite de girasol', 'Sal fina'],
        'precio': [25.50, 18.75, 12.00],
        'stock': [100, 50, 200],
        'stock_minimo': [20, 10, 30],
        'categoria': ['Harinas', 'Aceites', 'Condimentos'],
        'fabricante': ['Molino X', 'Aceitera Y', 'Sal Z'],
        'unidad': ['kg', 'litro', 'kg'],
        'codigo': ['HAR001', 'ACE001', 'SAL001']
    }
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Insumos')
    
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
        'descripcion': ['Pizza Muzzarella', 'Empanadas de carne x12', 'Ensalada Caesar'],
        'precio': [450.00, 280.00, 350.00],
        'stock': [0, 0, 0],
        'stock_minimo': [5, 10, 3],
        'stock_objetivo': [15, 30, 10],
        'categoria': ['Pizzas', 'Empanadas', 'Ensaladas'],
        'modelo': ['PIZZA-MUZ', 'EMP-CARNE', 'ENS-CAESAR'],
        'produccion_habilitada': ['si', 'si', 'no']
    }
    
    df = pd.DataFrame(data)
    
    # Crear archivo Excel en memoria
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Productos')
    
    output.seek(0)
    
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=plantilla_productos.xlsx'
    
    return response
