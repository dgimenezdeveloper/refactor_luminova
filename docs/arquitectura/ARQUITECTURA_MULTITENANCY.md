# Arquitectura Multi-Tenant de LUMINOVA

## Resumen Ejecutivo

LUMINOVA implementa un **multi-tenancy lógico** basado en filtrado por empresa. Esto significa que todos los datos de todas las empresas coexisten en la misma base de datos, pero se filtran por el campo `empresa` en cada modelo.

## Arquitectura Implementada

### Tipo de Multi-Tenancy: Filtrado Lógico (Single Database)

```
┌─────────────────────────────────────────────────────────────┐
│                    BASE DE DATOS ÚNICA                       │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              TODOS LOS MODELOS                           │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │ │
│  │  │Empresa 1│  │Empresa 2│  │Empresa 3│  │Empresa N│    │ │
│  │  │ (datos) │  │ (datos) │  │ (datos) │  │ (datos) │    │ │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘    │ │
│  │       │            │            │            │         │ │
│  │       └────────────┴──────┬─────┴────────────┘         │ │
│  │                           │                             │ │
│  │                    Filtrado por                         │ │
│  │                   campo "empresa"                       │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Ventajas de esta Arquitectura

| Aspecto | Beneficio |
|---------|-----------|
| **Simplicidad** | No requiere configuración especial de PostgreSQL |
| **Costo** | Una sola base de datos, menor costo operativo |
| **Migración** | Fácil migrar datos existentes |
| **Mantenimiento** | Un solo esquema para mantener |
| **Escalabilidad** | Adecuado para hasta ~100 empresas |

### Comparación con Alternativas

| Enfoque | LUMINOVA (actual) | django-tenants |
|---------|-------------------|----------------|
| Aislamiento | Por filtrado | Por esquema PostgreSQL |
| Complejidad | Baja | Alta |
| Base de datos | SQLite/PostgreSQL | Solo PostgreSQL |
| Migración | Simple | Compleja |
| Rendimiento | Bueno para <100 empresas | Mejor para >100 empresas |

---

## Modelos Multi-Tenant

### Modelo Base: `EmpresaScopedModel`

```python
class EmpresaScopedModel(models.Model):
    """Base abstracta para modelos aislados por empresa."""
    
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s",
        null=True,
        blank=True,
    )
    
    EMPRESA_FALLBACK_FIELDS = ()  # Campos para inferir empresa
    
    class Meta:
        abstract = True
```

### Lista Completa de Modelos Multi-Tenant

| Modelo | Hereda de | Campo Empresa | Estado |
|--------|-----------|---------------|--------|
| `Deposito` | `models.Model` | FK directo |  |
| `CategoriaInsumo` | `EmpresaScopedModel` | Heredado |  |
| `CategoriaProductoTerminado` | `EmpresaScopedModel` | Heredado |  |
| `Insumo` | `EmpresaScopedModel` | Heredado |  |
| `ProductoTerminado` | `EmpresaScopedModel` | Heredado |  |
| `Cliente` | `EmpresaScopedModel` | Heredado |  |
| `Proveedor` | `EmpresaScopedModel` | Heredado |  |
| `Fabricante` | `EmpresaScopedModel` | Heredado |  |
| `OrdenVenta` | `EmpresaScopedModel` | Heredado |  |
| `OrdenProduccion` | `EmpresaScopedModel` | Heredado |  |
| `Orden` | `EmpresaScopedModel` | Heredado |  |
| `ItemOrdenVenta` | `EmpresaScopedModel` | Heredado |  |
| `Factura` | `EmpresaScopedModel` | Heredado |  |
| `OfertaProveedor` | `EmpresaScopedModel` | Heredado |  |
| `ComponenteProducto` | `EmpresaScopedModel` | Heredado |  |
| `LoteProductoTerminado` | `EmpresaScopedModel` | Heredado |  |
| `StockInsumo` | `EmpresaScopedModel` | Heredado |  |
| `StockProductoTerminado` | `EmpresaScopedModel` | Heredado |  |
| `MovimientoStock` | `EmpresaScopedModel` | Heredado |  |
| `NotificacionSistema` | `EmpresaScopedModel` | Heredado |  |
| `HistorialOV` | `EmpresaScopedModel` | Heredado |  |
| `Reportes` | `EmpresaScopedModel` | Heredado |  |
| `UsuarioDeposito` | `models.Model` | FK directo |  |
| `EstadoOrden` | `models.Model` | FK directo |  |
| `SectorAsignado` | `models.Model` | FK directo |  |
| `AuditoriaAcceso` | `models.Model` | FK directo |  |
| `PerfilUsuario` | `models.Model` | FK directo |  |
| `RolEmpresa` | `models.Model` | FK directo |  |

### Modelos Compartidos (Sin Campo Empresa)

| Modelo | Razón |
|--------|-------|
| `Empresa` | Es el tenant mismo |
| `RolDescripcion` | Extensión de Groups de Django |
| `PasswordChangeRequired` | Control de seguridad global |
| `User` | Modelo de Django (usuarios vía PerfilUsuario) |

---

## Componentes del Sistema Multi-Tenant

### 1. Middleware: `EmpresaMiddleware`

**Ubicación:** `App_LUMINOVA/middleware.py`

```python
class EmpresaMiddleware:
    def __call__(self, request):
        # 1. Obtiene empresa de sesión
        # 2. Si no hay, obtiene de PerfilUsuario
        # 3. Asigna request.empresa_actual
        # 4. Guarda en thread-local para modelos
```

### 2. Thread-Locals: `threadlocals.py`

**Ubicación:** `App_LUMINOVA/threadlocals.py`

```python
def set_current_empresa(empresa):
    """Guarda empresa activa para acceso en modelos/señales."""
    
def get_current_empresa():
    """Retorna empresa activa fuera del contexto request."""
```

### 3. Filtros de Empresa: `empresa_filters.py`

**Ubicación:** `App_LUMINOVA/empresa_filters.py`

```python
def get_depositos_empresa(request)
def filter_insumos_por_empresa(request, queryset=None)
def filter_productos_por_empresa(request, queryset=None)
def filter_ordenes_venta_por_empresa(request, queryset=None)
def filter_ordenes_compra_por_empresa(request, queryset=None)
def filter_ordenes_produccion_por_empresa(request, queryset=None)
def filter_clientes_por_empresa(request, queryset=None)
def filter_proveedores_por_empresa(request, queryset=None)
def filter_fabricantes_por_empresa(request, queryset=None)
def filter_categorias_insumos_por_empresa(request, queryset=None)
def filter_categorias_productos_por_empresa(request, queryset=None)
```

### 4. Context Processors

**Ubicación:** `App_LUMINOVA/context_processors.py`

- `notificaciones_context(request)` - Contadores filtrados por empresa
- `puede_ver_deposito_sidebar(request)` - Permisos por empresa
- `empresa_actual_context(request)` - Datos de empresa para templates

---

## Flujo de Datos Multi-Tenant

```
┌─────────────┐
│   Usuario   │
│  (Login)    │
└──────┬──────┘
       │
       ▼
┌──────────────────────────┐
│    EmpresaMiddleware     │
│  - Obtiene PerfilUsuario │
│  - Asigna empresa_actual │
│  - Set thread-local      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│         Vista            │
│  - request.empresa_actual│
│  - Usa empresa_filters   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│     QuerySets            │
│  .filter(empresa=X)      │
└──────────────────────────┘
```

---

## Asignación Automática de Empresa

### En Modelos (EmpresaScopedModel)

```python
def save(self, *args, **kwargs):
    self.ensure_empresa()  # Auto-asigna empresa
    super().save(*args, **kwargs)

def ensure_empresa(self):
    # 1. Si ya tiene empresa, retornar
    # 2. Inferir desde relaciones (EMPRESA_FALLBACK_FIELDS)
    # 3. Usar empresa del thread-local
```

### Ejemplo: UsuarioDeposito

```python
def save(self, *args, **kwargs):
    if not self.empresa_id and self.deposito_id:
        self.empresa = self.deposito.empresa  # Inferir de depósito
    super().save(*args, **kwargs)
```

---

## Verificación de Integridad

### Script de Verificación

```bash
python verificar_multitenancy.py
```

**Verifica:**
1.  Todos los modelos tienen campo `empresa`
2.  Todos los registros tienen empresa asignada
3.  Las relaciones son consistentes
4.  Distribución de datos por empresa

---

## Guía para Nuevos Desarrolladores

### Crear un Nuevo Modelo Multi-Tenant

```python
class MiNuevoModelo(EmpresaScopedModel):
    EMPRESA_FALLBACK_FIELDS = ("relacion_padre",)  # Opcional
    
    # campos del modelo
    nombre = models.CharField(max_length=100)
    relacion_padre = models.ForeignKey(OtroModelo, on_delete=models.CASCADE)
```

### Filtrar Datos en una Vista

```python
from .empresa_filters import filter_insumos_por_empresa

@login_required
def mi_vista(request):
    insumos = filter_insumos_por_empresa(request)
    # O directamente:
    # insumos = Insumo.objects.filter(empresa=request.empresa_actual)
```

### Crear un Nuevo Filtro

```python
# En empresa_filters.py
def filter_mi_modelo_por_empresa(request, queryset=None):
    if queryset is None:
        queryset = MiModelo.objects.all()
    return _filter_queryset_by_empresa(request, queryset)
```

---

## Migraciones Aplicadas

| Migración | Descripción |
|-----------|-------------|
| `0029_empresa_alter_deposito_nombre_deposito_empresa_and_more` | Crea modelo Empresa, agrega a Deposito |
| `0030_set_empresa_non_nullable` | Configura empresa no nullable |
| `0031_perfilusuario` | Crea PerfilUsuario |
| `0032_categoriainsumo_empresa_and_more` | Agrega empresa a modelos principales |
| `0033_rolempresa` | Crea RolEmpresa |
| `0034_alter_rolempresa_unique_together_rolempresa_nombre_and_more` | Ajusta RolEmpresa |
| `0035_complete_multitenancy` | Completa multi-tenancy: UsuarioDeposito, EstadoOrden, SectorAsignado, AuditoriaAcceso |

---

## Estado Actual

```
 SISTEMA MULTI-TENANT VERIFICADO CORRECTAMENTE
   - Todos los modelos tienen campo empresa
   - Todos los registros tienen empresa asignada
   - Las relaciones son consistentes
```

### Distribución de Empresas

| Empresa | Depósitos | Insumos | Productos | Usuarios |
|---------|-----------|---------|-----------|----------|
| Luminova ERP | 3 | 67 | 11 | 5 |
| Sabores del Valle | 3 | 0 | 0 | 1 |

---

## Próximos Pasos (Opcional)

1. **Migrar a PostgreSQL** para producción (mejor rendimiento)
2. **Agregar índices compuestos** `(empresa, campo_frecuente)` si hay problemas de rendimiento
3. **Evaluar django-tenants** si se superan las 100 empresas
4. **Implementar caché** de empresa por usuario para reducir queries

---

*Última actualización: 2026-01-11*
