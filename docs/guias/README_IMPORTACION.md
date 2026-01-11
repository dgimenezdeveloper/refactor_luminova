# Sistema de Importación Masiva - LUMINOVA

## Descripción

Sistema flexible de importación masiva de datos adaptable a cualquier rubro empresarial. Permite cargar insumos y productos terminados desde archivos CSV o Excel.

## Características

-  **Multi-empresa**: Aislamiento automático de datos por empresa
-  **Flexible**: Acepta múltiples nombres de columnas (aliases)
-  **Inteligente**: Creación automática de categorías y fabricantes
-  **Robusto**: Validación exhaustiva con reportes detallados
-  **Universal**: Adaptable a manufactura, gastronomía, retail, etc.

## Arquitectura

### Componentes Principales

```
App_LUMINOVA/
├── views_importacion.py              # Vistas de importación
├── urls/importacion_urls.py          # URLs del módulo
├── templates/importacion/            # Templates de UI
│   ├── importacion_principal.html
│   ├── importar_insumos.html
│   └── importar_productos.html
└── services/importacion/             # Lógica de negocio
    ├── base_importer.py              # Clase abstracta base
    ├── insumo_importer.py            # Importador de insumos
    └── producto_importer.py          # Importador de productos
```

### Clases de Importación

#### BaseImporter (Abstracta)
Clase base con funcionalidad común:
- Lectura de archivos CSV/Excel con pandas
- Validación de estructura de datos
- Sistema de logging y errores
- Normalización de nombres de columnas

#### InsumoImporter
Importador específico para insumos/materias primas:
- Aliases flexibles: "descripcion", "nombre", "insumo", "ingrediente", "material"
- Creación automática de categorías de insumos
- Gestión de fabricantes opcionales
- Validación de stocks y precios

#### ProductoImporter
Importador para productos terminados:
- Aliases flexibles: "descripcion", "nombre", "producto", "plato", "servicio"
- Creación automática de categorías de productos
- Gestión de precios (venta y costo)
- Control de producción habilitada

## Uso

### 1. Acceder al módulo
Navegar a: `/importacion/` o usar el menú lateral -> **Importación**

### 2. Descargar plantilla
Hacer clic en "Descargar Plantilla" para obtener un archivo Excel de ejemplo.

### 3. Completar datos
Editar el archivo con los datos reales. 

#### Columnas para Insumos:
- **Requeridas**: `descripcion`, `categoria`, `stock`, `unidad`
- **Opcionales**: `codigo`, `fabricante`, `precio_unitario`, `stock_minimo`, `ubicacion`

#### Columnas para Productos:
- **Requeridas**: `descripcion`, `categoria`, `precio_venta`
- **Opcionales**: `codigo`, `stock`, `stock_minimo`, `precio_costo`, `produccion_habilitada`

### 4. Cargar archivo
Subir el archivo CSV o Excel completado.

### 5. Revisar resultados
El sistema mostrará:
-  Registros importados correctamente
-  Advertencias (datos corregidos automáticamente)
-  Errores (registros rechazados con explicación)

## Ejemplos

### Ejemplo 1: Empresa de Manufactura

**Insumos:**
```csv
descripcion,categoria,stock,unidad,codigo,precio_unitario
"Madera de Roble","Maderas",150,"m2","MAD-001",4500.00
"Barniz Transparente","Químicos",80,"litros","QUI-010",890.50
```

**Productos:**
```csv
descripcion,categoria,precio_venta,codigo,produccion_habilitada
"Mesa de Comedor 6 Personas","Mesas",125000.00,"MES-001","Sí"
"Silla de Roble Moderna","Sillas",18500.00,"SIL-001","Sí"
```

### Ejemplo 2: Empresa de Gastronomía

**Ingredientes (Insumos):**
```csv
ingrediente,categoria,stock,unidad,fabricante
"Harina 000","Harinas y Panificación",250,"kg","Molinos del Sur"
"Tomate Perita","Conservas",180,"kg","La Huerta SA"
"Muzzarella","Lácteos",80,"kg","Tambos Unidos"
```

**Platos (Productos):**
```csv
plato,categoria,precio_venta,codigo
"Pizza Margarita Grande","Pizzas",3500.00,"PIZ-MAR-G"
"Ensalada César con Pollo","Ensaladas",2800.00,"ENS-CES"
"Milanesa Napolitana","Platos Principales",4200.00,"MIL-NAP"
```

## Aliases de Columnas

El sistema reconoce automáticamente múltiples nombres para cada campo:

### Descripción
- `descripcion`, `nombre`, `producto`, `item`, `insumo`, `material`, `ingrediente`, `plato`, `servicio`

### Categoría
- `categoria`, `tipo`, `grupo`, `familia`

### Stock
- `stock`, `stock_actual`, `cantidad`, `existencia`

### Precio
- `precio`, `precio_unitario`, `costo`, `valor`, `pvp`, `precio_venta`

### Código
- `codigo`, `sku`, `modelo`, `referencia`

## Validaciones

El sistema valida automáticamente:
-  Campos requeridos presentes
-  Tipos de datos correctos (números, textos)
-  Valores numéricos positivos (stocks, precios)
-  Unicidad de códigos/SKUs
-  Longitud máxima de textos

## Aislamiento Multi-empresa

Cada importación:
- Se asocia automáticamente a la empresa actual del usuario
- Solo puede acceder a depósitos de su empresa
- Las categorías creadas son exclusivas de la empresa
- No hay riesgo de mezclar datos entre empresas

## Archivos de Ejemplo

Se incluyen 4 archivos CSV de ejemplo en `plantillas_importacion/`:

1. `insumos_manufactura_ejemplo.csv` - Insumos para empresa manufacturera
2. `productos_manufactura_ejemplo.csv` - Productos para manufactura
3. `insumos_gastronomia_ejemplo.csv` - Ingredientes para gastronomía
4. `productos_gastronomia_ejemplo.csv` - Platos/comidas para gastronomía

## Extensión

Para agregar nuevos tipos de importación:

1. Crear una nueva clase heredando de `BaseImporter`
2. Implementar métodos abstractos: `validate_row`, `transform_row`, `import_row`
3. Definir aliases de columnas en `FIELD_ALIASES`
4. Agregar vista en `views_importacion.py`
5. Crear template correspondiente
6. Registrar URL en `importacion_urls.py`

## Dependencias

- `pandas>=2.0.0` - Lectura/procesamiento de CSV/Excel
- `openpyxl>=3.0.0` - Soporte para archivos .xlsx
- `Django>=5.0` - Framework web

## Testing

Para probar la funcionalidad:

```bash
# 1. Activar entorno virtual
source env/bin/activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar servidor
python manage.py runserver

# 4. Acceder a http://localhost:8000/importacion/

# 5. Usar archivos de ejemplo en plantillas_importacion/
```

## Troubleshooting

### Error: "No module named 'pandas'"
```bash
pip install pandas openpyxl
```

### Error: "No hay depósitos configurados"
- Crear al menos un depósito para la empresa actual
- Verificar que el usuario tenga perfil asignado a una empresa

### Advertencia: "Categoría no encontrada"
- El sistema la creará automáticamente
- No es un error, solo un aviso informativo

### Error en importación: "Registro X tiene errores"
- Revisar el mensaje específico de error
- Corregir el archivo y volver a importar
- Los registros válidos se procesarán correctamente

## Autores

- Equipo de Desarrollo LUMINOVA
- Fecha: 2025

## Licencia

Uso interno - LUMINOVA ERP System
