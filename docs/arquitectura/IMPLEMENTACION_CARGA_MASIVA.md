# Implementación de Carga Masiva de Datos - LUMINOVA
## Sistema de Importación Flexible Multi-Rubro

**Fecha de Implementación**: 14 de enero de 2026  
**Estado**: ✅ Implementado  
**Relacionado con**: [Análisis Crítica Constructiva](ANALISIS_CRITICA_CONSTRUCTIVA.md)

---

## 📋 Resumen Ejecutivo

Este documento describe la implementación del sistema de carga masiva de datos para LUMINOVA. El sistema permite importar grandes volúmenes de datos desde archivos CSV y Excel, con validación automática, creación de entidades relacionadas y registro de historial.

---

## 🎯 Objetivos de la Implementación

### Objetivos Principales
1. **Permitir importación masiva** de insumos, productos, clientes y proveedores
2. **Validar datos automáticamente** antes de la importación
3. **Crear entidades relacionadas** (categorías, fabricantes) si no existen
4. **Registrar historial** de todas las importaciones
5. **Proporcionar plantillas** descargables con ejemplos

### Beneficios
- ✅ Carga inicial rápida de datos para nuevas empresas
- ✅ Migración de datos desde sistemas externos
- ✅ Actualización masiva de precios y stocks
- ✅ Auditoría completa de importaciones
- ✅ Flexibilidad en formatos de archivo

---

## 🏗️ Arquitectura del Sistema

### Estructura de Archivos

```
App_LUMINOVA/
├── services/
│   └── importacion/
│       ├── __init__.py
│       ├── base_importer.py      # Clase base con lógica común
│       ├── insumo_importer.py    # Importador de insumos
│       ├── producto_importer.py  # Importador de productos
│       ├── cliente_importer.py   # Importador de clientes
│       └── proveedor_importer.py # Importador de proveedores
├── views_importacion.py          # Vistas del módulo
├── urls/
│   └── importacion_urls.py       # URLs del módulo
└── templates/
    └── importacion/
        ├── importacion_principal.html
        ├── importar_insumos.html
        ├── importar_productos.html
        ├── importar_clientes.html
        ├── importar_proveedores.html
        └── historial.html
```

### Modelo de Datos

```python
class HistorialImportacion(EmpresaScopedModel):
    """Registra el historial de importaciones masivas"""
    
    usuario = models.ForeignKey(User, ...)
    tipo_importacion = models.CharField(choices=[
        ('insumos', 'Insumos'),
        ('productos', 'Productos Terminados'),
        ('clientes', 'Clientes'),
        ('proveedores', 'Proveedores'),
    ])
    nombre_archivo = models.CharField(max_length=255)
    fecha_importacion = models.DateTimeField(default=timezone.now)
    registros_importados = models.PositiveIntegerField(default=0)
    registros_actualizados = models.PositiveIntegerField(default=0)
    registros_con_error = models.PositiveIntegerField(default=0)
    exitoso = models.BooleanField(default=False)
    deposito = models.ForeignKey('Deposito', null=True, blank=True)
    errores_detalle = models.JSONField(default=list)
    warnings_detalle = models.JSONField(default=list)
```

---

## 📡 Endpoints Disponibles

### URLs de Importación

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/importacion/` | GET | Dashboard principal de importación |
| `/importacion/importar/insumos/` | GET, POST | Importar insumos |
| `/importacion/importar/productos/` | GET, POST | Importar productos |
| `/importacion/importar/clientes/` | GET, POST | Importar clientes |
| `/importacion/importar/proveedores/` | GET, POST | Importar proveedores |
| `/importacion/historial/` | GET | Historial de importaciones |
| `/importacion/plantilla/insumos/` | GET | Descargar plantilla insumos |
| `/importacion/plantilla/productos/` | GET | Descargar plantilla productos |
| `/importacion/plantilla/clientes/` | GET | Descargar plantilla clientes |
| `/importacion/plantilla/proveedores/` | GET | Descargar plantilla proveedores |

---

## 🔧 Características Técnicas

### Formatos Soportados
- **CSV** (con detección automática de encoding UTF-8/Latin-1)
- **Excel** (.xlsx, .xls)

### Sistema de Aliases
El sistema acepta múltiples nombres de columnas para facilitar la importación:

```python
FIELD_ALIASES = {
    'descripcion': ['descripcion', 'nombre', 'producto', 'item', 'artículo'],
    'precio': ['precio', 'precio_unitario', 'costo', 'valor'],
    'stock': ['stock', 'cantidad', 'existencia'],
    'categoria': ['categoria', 'categoría', 'tipo', 'grupo', 'familia'],
    # ... más aliases
}
```

### Validación de Datos
- Campos obligatorios (descripción/nombre)
- Formato de precios (no negativos)
- Formato de stocks (enteros no negativos)
- Validación de emails
- Detección de duplicados

### Creación Automática
- **Categorías**: Si no existe la categoría, se crea automáticamente
- **Fabricantes**: Si no existe el fabricante, se crea automáticamente
- **Depósitos**: Se asocia al depósito seleccionado

---

## 📝 Guía de Uso

### 1. Preparar el archivo

Descargar la plantilla correspondiente desde el dashboard de importación. Las plantillas incluyen:
- Hoja de datos de ejemplo
- Hoja de instrucciones con aliases permitidos

### 2. Completar los datos

| Campo | Obligatorio | Descripción |
|-------|-------------|-------------|
| descripcion | ✅ Sí | Nombre del item |
| precio | No | Precio unitario |
| stock | No | Stock inicial |
| categoria | No | Categoría (se crea si no existe) |

### 3. Importar

1. Ir a `/importacion/`
2. Seleccionar tipo de importación
3. Seleccionar depósito destino (para insumos/productos)
4. Subir archivo
5. Revisar resultados

### 4. Verificar historial

El historial muestra:
- Total de registros importados
- Registros actualizados
- Errores encontrados
- Estadísticas globales

---

## 🔄 Flujo de Importación

```
┌─────────────────┐
│ Subir Archivo   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Leer CSV/Excel  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Normalizar      │
│ Columnas        │
│ (Aliases)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Validar         │
│ Estructura      │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│ Por cada fila:                  │
│ 1. Validar datos               │
│ 2. Transformar formato         │
│ 3. Crear/Actualizar registro   │
│ 4. Registrar resultado         │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Guardar         │
│ Historial       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Mostrar         │
│ Resultados      │
└─────────────────┘
```

---

## 📊 Estadísticas del Historial

El sistema registra y muestra:
- **Total de importaciones** realizadas
- **Total de registros** importados exitosamente
- **Total de registros** actualizados
- **Total de errores** encontrados

---

## 🔒 Seguridad

- **Autenticación requerida**: Todas las vistas requieren login
- **Aislamiento multi-tenant**: Los datos se asocian a la empresa del usuario
- **Archivos temporales**: Se eliminan después de procesar
- **Validación de entrada**: Todos los datos se validan antes de insertar

---

## 🚀 Mejoras Futuras Sugeridas

1. **Importación asíncrona** con Celery para archivos grandes
2. **Vista previa** de datos antes de importar
3. **Mapeo personalizado** de columnas por empresa
4. **Importación de BOM** (Bill of Materials)
5. **Exportación masiva** de datos
6. **API REST** para importación programática
7. **Importación de ofertas de proveedores**

---

## 📁 Dependencias

El sistema utiliza las siguientes librerías:
- `pandas` - Lectura de CSV/Excel
- `openpyxl` - Generación de archivos Excel

Asegurarse de que estén en `requirements.txt`:
```
pandas>=2.0.0
openpyxl>=3.1.0
```

---

**Documento generado el**: 14 de enero de 2026  
**Próxima revisión recomendada**: Tras implementar importación asíncrona
