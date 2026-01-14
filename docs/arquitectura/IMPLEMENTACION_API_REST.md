# Implementación de APIs REST - LUMINOVA
## Sistema ERP Multi-depósito con Django REST Framework

**Fecha de Implementación**: 14 de enero de 2026  
**Estado**: ✅ Implementado  
**Relacionado con**: [Análisis Crítica Constructiva](ANALISIS_CRITICA_CONSTRUCTIVA.md)

---

## 📋 Resumen Ejecutivo

Este documento describe la implementación completa de APIs REST para el sistema LUMINOVA, utilizando Django REST Framework (DRF). La API está diseñada con soporte completo para multi-tenancy, autenticación basada en tokens/sesión, y documentación automática.

---

## 🎯 Objetivos de la Implementación

### Objetivos Principales
1. **Exponer endpoints RESTful** para todas las entidades principales del sistema
2. **Mantener aislamiento multi-tenant** en todas las operaciones
3. **Proporcionar autenticación segura** con múltiples métodos
4. **Documentar automáticamente** la API con OpenAPI/Swagger
5. **Permitir integración** con sistemas externos y aplicaciones frontend modernas

### Beneficios
- ✅ Integración con aplicaciones móviles futuras
- ✅ Desarrollo de frontend SPA (Vue.js, React)
- ✅ Conexión con sistemas de terceros
- ✅ Automatización de procesos mediante scripts
- ✅ Base para microservicios futuros

---

## 🏗️ Arquitectura de la API

### Estructura de Archivos

```
App_LUMINOVA/
├── api/
│   ├── __init__.py
│   ├── serializers.py      # Serializadores para todos los modelos
│   ├── viewsets.py         # ViewSets con lógica de negocio
│   ├── permissions.py      # Permisos personalizados multi-tenant
│   ├── filters.py          # Filtros para búsquedas avanzadas
│   └── pagination.py       # Configuración de paginación
├── urls/
│   └── api_urls.py         # Rutas de la API (actualizado)
```

### Versionado de API

La API utiliza versionado por URL:
- **v1**: `/api/v1/` - Versión estable actual

---

## 🔐 Autenticación y Seguridad

### Métodos de Autenticación Soportados

1. **Session Authentication** - Para frontend Django tradicional
2. **Token Authentication** - Para aplicaciones externas
3. **Basic Authentication** - Para desarrollo/testing

### Aislamiento Multi-Tenant

Todos los endpoints filtran automáticamente por empresa del usuario autenticado:

```python
class EmpresaScopedViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        empresa = self.request.user.perfil.empresa
        return self.queryset.filter(empresa=empresa)
```

---

## 📡 Endpoints Disponibles

### Catálogos Base

| Endpoint | Métodos | Descripción |
|----------|---------|-------------|
| `/api/v1/categorias-producto/` | GET, POST, PUT, DELETE | Categorías de productos terminados |
| `/api/v1/categorias-insumo/` | GET, POST, PUT, DELETE | Categorías de insumos |
| `/api/v1/depositos/` | GET, POST, PUT, DELETE | Gestión de depósitos |
| `/api/v1/proveedores/` | GET, POST, PUT, DELETE | Proveedores |
| `/api/v1/fabricantes/` | GET, POST, PUT, DELETE | Fabricantes |
| `/api/v1/clientes/` | GET, POST, PUT, DELETE | Clientes |

### Inventario

| Endpoint | Métodos | Descripción |
|----------|---------|-------------|
| `/api/v1/productos/` | GET, POST, PUT, DELETE | Productos terminados |
| `/api/v1/insumos/` | GET, POST, PUT, DELETE | Insumos/materias primas |
| `/api/v1/ofertas-proveedor/` | GET, POST, PUT, DELETE | Ofertas de proveedores |
| `/api/v1/componentes-producto/` | GET, POST, PUT, DELETE | BOM (Bill of Materials) |
| `/api/v1/stock-insumos/` | GET, POST | Stock de insumos por depósito |
| `/api/v1/stock-productos/` | GET, POST | Stock de productos por depósito |
| `/api/v1/movimientos-stock/` | GET, POST | Movimientos de stock |

### Ventas

| Endpoint | Métodos | Descripción |
|----------|---------|-------------|
| `/api/v1/ordenes-venta/` | GET, POST, PUT, DELETE | Órdenes de venta |
| `/api/v1/items-orden-venta/` | GET, POST, PUT, DELETE | Items de órdenes de venta |
| `/api/v1/facturas/` | GET, POST | Facturas |

### Producción

| Endpoint | Métodos | Descripción |
|----------|---------|-------------|
| `/api/v1/ordenes-produccion/` | GET, POST, PUT, DELETE | Órdenes de producción |
| `/api/v1/estados-orden/` | GET, POST, PUT, DELETE | Estados de orden |
| `/api/v1/sectores/` | GET, POST, PUT, DELETE | Sectores de producción |
| `/api/v1/lotes-producto/` | GET, POST | Lotes de producto terminado |
| `/api/v1/reportes-produccion/` | GET, POST, PUT | Reportes de incidencias |

### Compras

| Endpoint | Métodos | Descripción |
|----------|---------|-------------|
| `/api/v1/ordenes-compra/` | GET, POST, PUT, DELETE | Órdenes de compra |

### Sistema

| Endpoint | Métodos | Descripción |
|----------|---------|-------------|
| `/api/v1/notificaciones/` | GET, POST, PUT | Notificaciones del sistema |
| `/api/v1/usuarios-deposito/` | GET, POST, PUT, DELETE | Asignación usuarios-depósito |
| `/api/v1/auditorias/` | GET | Registro de auditoría (solo lectura) |

### Autenticación

| Endpoint | Métodos | Descripción |
|----------|---------|-------------|
| `/api/v1/auth/token/` | POST | Obtener token de autenticación |
| `/api/v1/auth/user/` | GET | Información del usuario actual |

---

## 📝 Ejemplos de Uso

### Obtener Token de Autenticación

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "usuario", "password": "contraseña"}'
```

**Respuesta:**
```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

### Listar Productos Terminados

```bash
curl -X GET http://localhost:8000/api/v1/productos/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

**Respuesta:**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/productos/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "descripcion": "Lámpara LED 50W",
      "categoria": 1,
      "categoria_nombre": "Iluminación LED",
      "precio_unitario": "1500.00",
      "stock": 45,
      "stock_minimo": 10,
      "stock_objetivo": 100,
      "necesita_reposicion": false,
      "deposito": 1,
      "deposito_nombre": "Depósito Central"
    }
  ]
}
```

### Crear Orden de Venta

```bash
curl -X POST http://localhost:8000/api/v1/ordenes-venta/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente": 1,
    "notas": "Entrega urgente"
  }'
```

### Filtros Disponibles

```bash
# Filtrar productos por categoría
GET /api/v1/productos/?categoria=5

# Filtrar por depósito
GET /api/v1/productos/?deposito=1

# Buscar por descripción
GET /api/v1/productos/?search=lámpara

# Productos que necesitan reposición
GET /api/v1/productos/?necesita_reposicion=true

# Ordenar por stock
GET /api/v1/productos/?ordering=stock

# Combinar filtros
GET /api/v1/productos/?categoria=5&deposito=1&ordering=-precio_unitario
```

---

## ⚙️ Configuración

### Dependencias Añadidas

```txt
# requirements.txt
djangorestframework==3.14.0
django-filter==23.5
drf-spectacular==0.27.0
```

### Configuración en settings.py

```python
INSTALLED_APPS = [
    # ... apps existentes
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'LUMINOVA API',
    'DESCRIPTION': 'API REST para Sistema ERP Multi-depósito LUMINOVA',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
```

---

## 📚 Documentación Interactiva

Una vez configurada la API, la documentación interactiva está disponible en:

- **Swagger UI**: `/api/docs/`
- **ReDoc**: `/api/redoc/`
- **Schema OpenAPI**: `/api/schema/`

---

## 🔄 Próximos Pasos

### Fase 2 - Mejoras Planificadas
1. [ ] Implementar autenticación JWT
2. [ ] Agregar rate limiting
3. [ ] Implementar webhooks para eventos
4. [ ] Endpoints bulk para operaciones masivas
5. [ ] Versionado API v2 con mejoras

### Integración con Frontend
1. [ ] Cliente JavaScript/TypeScript generado desde OpenAPI
2. [ ] SDK para Vue.js
3. [ ] Documentación de integración

---

## 📊 Métricas y Monitoreo

### Headers de Respuesta Útiles
- `X-Request-ID`: Identificador único de request para debugging
- `X-RateLimit-Remaining`: Requests restantes (cuando se implemente)

### Códigos de Estado HTTP

| Código | Significado |
|--------|-------------|
| 200 | OK - Operación exitosa |
| 201 | Created - Recurso creado |
| 204 | No Content - Eliminación exitosa |
| 400 | Bad Request - Error en datos enviados |
| 401 | Unauthorized - No autenticado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 500 | Internal Server Error |

---

## 📁 Archivos Implementados

| Archivo | Descripción |
|---------|-------------|
| [App_LUMINOVA/api/__init__.py](../../App_LUMINOVA/api/__init__.py) | Inicialización del módulo API |
| [App_LUMINOVA/api/serializers.py](../../App_LUMINOVA/api/serializers.py) | Serializadores de modelos |
| [App_LUMINOVA/api/viewsets.py](../../App_LUMINOVA/api/viewsets.py) | ViewSets con lógica de negocio |
| [App_LUMINOVA/api/permissions.py](../../App_LUMINOVA/api/permissions.py) | Permisos multi-tenant |
| [App_LUMINOVA/api/filters.py](../../App_LUMINOVA/api/filters.py) | Filtros de búsqueda |
| [App_LUMINOVA/urls/api_urls.py](../../App_LUMINOVA/urls/api_urls.py) | Rutas de la API |

---

**Documento creado el**: 14 de enero de 2026  
**Última actualización**: 14 de enero de 2026  
**Autor**: Equipo de Desarrollo LUMINOVA

---

## 🐛 Problemas Resueltos Durante la Implementación

### Problema 1: FieldError por Campo `stock` Normalizado

**Descripción**: Después de la normalización de la base de datos, el campo `stock` fue movido de los modelos `Insumo` y `ProductoTerminado` a tablas separadas (`StockInsumo`, `StockProductoTerminado`). Esto causó `FieldError: Cannot resolve keyword 'stock' into field` en múltiples vistas.

**Archivos Afectados**:
- `views_auth.py`
- `views_deposito.py` 
- `views_producción.py`
- `views_compras.py`
- `context_processors.py`
- `forms.py`
- `management/commands/stock_management.py`
- `management/commands/generar_ops_stock_automaticas.py`

**Solución Implementada**:
1. Se crearon funciones helper en `utils.py`:
   - `annotate_insumo_stock()`: Anota querysets con stock calculado
   - `annotate_producto_stock()`: Anota querysets de productos con stock
   - `get_insumos_stock_bajo()`: Retorna insumos con stock bajo ya anotados
   - `get_productos_necesitan_reposicion()`: Retorna productos necesitando reposición

2. Se actualizaron todas las referencias de `stock__lt`, `stock__gt`, etc. para usar `stock_calculado__lt`, `stock_calculado__gt` con querysets anotados.

3. Se actualizaron las referencias a `insumo.stock` y `producto.stock` para usar `getattr(obj, 'stock_calculado', 0)`.

### Problema 2: Error en Serialización de GenericIPAddressField

**Descripción**: El serializador `AuditoriaAccesoSerializer` generaba `ValueError: not enough values to unpack` al intentar generar el schema OpenAPI debido a incompatibilidad con `GenericIPAddressField`.

**Solución**: Se definió explícitamente el campo `ip_address` como `CharField` en el serializer:

```python
class AuditoriaAccesoSerializer(serializers.ModelSerializer):
    ip_address = serializers.CharField(read_only=True, allow_null=True)
```

### Verificación Final

✅ Servidor Django inicia sin errores  
✅ Dashboard principal funciona correctamente  
✅ API endpoints responden (401 sin autenticación)  
✅ Schema OpenAPI se genera correctamente  
✅ Documentación Swagger UI accesible en `/api/docs/`
