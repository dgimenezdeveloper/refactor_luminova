#  Inicio Rápido - Sistema de Importación LUMINOVA

##  Configuración Inicial (Primera vez)

```bash
# 1. Activar entorno virtual
source env/bin/activate

# 2. Instalar dependencias (si no están instaladas)
pip install -r requirements.txt

# 3. Verificar que todo está bien
python manage.py check

# 4. Ejecutar servidor
python manage.py runserver
```

##  Acceder al Sistema

1. Abrir navegador en: **http://localhost:8000**
2. Iniciar sesión:
   - Usuario: `admin`
   - Contraseña: (tu contraseña de admin)

##  Probar Importación en 5 Pasos

### Paso 1: Ir al módulo de importación
- Hacer clic en **"Importación"** en el menú lateral (sidebar)
- O navegar a: http://localhost:8000/importacion/

### Paso 2: Elegir tipo de importación
- **Importar Insumos**: Para materias primas, ingredientes, materiales
- **Importar Productos**: Para productos terminados, platos, artículos

### Paso 3: Usar archivo de ejemplo
**Opción A - Descargar plantilla:**
- Hacer clic en "Descargar Plantilla"
- Editar el archivo Excel con tus datos

**Opción B - Usar ejemplos incluidos:**
```bash
# Archivos CSV de ejemplo en:
plantillas_importacion/

Manufactura:
- insumos_manufactura_ejemplo.csv
- productos_manufactura_ejemplo.csv

Gastronomía:
- insumos_gastronomia_ejemplo.csv
- productos_gastronomia_ejemplo.csv
```

### Paso 4: Subir archivo
- Hacer clic en "Seleccionar archivo"
- Elegir CSV o Excel
- (Opcional) Marcar "Actualizar existentes"
- Hacer clic en "Iniciar Importación"

### Paso 5: Revisar resultados
El sistema mostrará:
-  Registros importados correctamente
-  Advertencias (se corrigieron automáticamente)
-  Errores (qué falló y por qué)

##  Cambiar de Empresa

1. Hacer clic en el selector de empresas (esquina superior)
2. Seleccionar empresa deseada
3. Todas las operaciones se harán en esa empresa

**Empresas configuradas:**
- **Luminova ERP** (Manufactura)
- **Sabores del Valle** (Gastronomía)

##  Usuarios de Prueba

| Usuario | Empresa | Tipo |
|---------|---------|------|
| admin | Luminova ERP | Superusuario |
| fpaal | Sabores del Valle | Usuario normal |
| chef_admin | Sabores del Valle | Usuario normal |

##  Formato de Archivos

### Insumos - Columnas aceptadas:

**Requeridas:**
- `descripcion` (o: nombre, insumo, ingrediente, material)
- `categoria`
- `stock`
- `unidad` (kg, litros, unidades, etc.)

**Opcionales:**
- `codigo` / `sku`
- `fabricante`
- `precio_unitario`
- `stock_minimo`
- `ubicacion`

### Productos - Columnas aceptadas:

**Requeridas:**
- `descripcion` (o: nombre, producto, plato, servicio)
- `categoria`
- `precio_venta`

**Opcionales:**
- `codigo` / `sku` / `modelo`
- `stock`
- `stock_minimo`
- `precio_costo`
- `produccion_habilitada` (Sí/No)

##  Ejemplos Rápidos

### Ejemplo 1: Manufactura
```csv
descripcion,categoria,stock,unidad,precio_unitario
"Madera de Roble","Maderas",150,"m2",4500.00
"Barniz Transparente","Químicos",80,"litros",890.50
```

### Ejemplo 2: Gastronomía
```csv
plato,categoria,precio_venta
"Pizza Margarita","Pizzas",3500.00
"Ensalada César","Ensaladas",2800.00
```

##  Troubleshooting Rápido

### Error: "No module named 'pandas'"
```bash
pip install pandas openpyxl
```

### Error: "No hay depósitos configurados"
- Crear un depósito para la empresa actual
- Verificar perfil de usuario

### No puedo acceder al módulo de importación
- Verificar que estás logueado
- Verificar que tu usuario tiene perfil asignado

### Los datos no aparecen
- Verificar que estás en la empresa correcta
- Cambiar de empresa usando el selector

##  Más Información

- **Documentación completa**: `README_IMPORTACION.md`
- **Resumen técnico**: `RESUMEN_IMPLEMENTACION.md`
- **Archivos de ejemplo**: `plantillas_importacion/`

## 🆘 Soporte

Para más ayuda:
1. Revisar documentación en `README_IMPORTACION.md`
2. Verificar logs del servidor
3. Revisar mensajes de error detallados en pantalla

---

**¡Listo para importar datos! **
