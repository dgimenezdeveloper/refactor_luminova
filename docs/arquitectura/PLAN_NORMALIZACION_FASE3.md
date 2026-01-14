# Plan de Normalización de Base de Datos - LUMINOVA
## Fase 3: Optimizaciones y Performance

**Fecha**: 14 de enero de 2026  
**Estado**: ✅ COMPLETADO  
**Prerrequisito**: [PLAN_NORMALIZACION_FASE2.md](PLAN_NORMALIZACION_FASE2.md) - Fase 2 Completada

---

## 📋 Objetivos de la Fase 3

### 1. ✅ Índices Estratégicos
Agregar índices a campos frecuentemente consultados para mejorar performance.

### 2. ✅ Ordenamiento por defecto optimizado
Configurar `ordering` en Meta de modelos para queries consistentes.

### 3. ✅ Índices compuestos para queries comunes
Índices multi-columna para consultas frecuentes.

---

## 🔍 Análisis de Queries Comunes

### Patrones de consulta identificados:

| Modelo | Filtros comunes | Ordenamiento frecuente |
|--------|----------------|----------------------|
| `OrdenVenta` | empresa, estado, fecha_creacion | -fecha_creacion |
| `Orden` (OC) | empresa, estado, deposito, proveedor | -fecha_creacion |
| `OrdenProduccion` | empresa, estado_op, producto_a_producir | -fecha_solicitud |
| `ProductoTerminado` | empresa, deposito, categoria | descripcion |
| `Insumo` | empresa, deposito, categoria | descripcion |
| `StockInsumo` | insumo, deposito | - |
| `StockProductoTerminado` | producto, deposito | - |
| `MovimientoStock` | empresa, deposito_origen, deposito_destino, fecha | -fecha |
| `Cliente` | empresa, nombre | nombre |
| `Proveedor` | empresa, nombre | nombre |

---

## 🔧 Cambios a Implementar

### Paso 1: Agregar índices a modelos clave

```python
# OrdenVenta - Consultas frecuentes por estado y fecha
class OrdenVenta(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['empresa', 'fecha_creacion']),
            models.Index(fields=['estado', 'fecha_creacion']),
        ]
        ordering = ['-fecha_creacion']

# Orden (OC) - Consultas por estado, depósito, proveedor
class Orden(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['empresa', 'deposito']),
            models.Index(fields=['estado', 'fecha_creacion']),
            models.Index(fields=['proveedor', 'estado']),
        ]
        ordering = ['-fecha_creacion']

# OrdenProduccion - Consultas por estado y producto
class OrdenProduccion(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'estado_op']),
            models.Index(fields=['producto_a_producir', 'estado_op']),
            models.Index(fields=['orden_venta_origen']),
        ]
        ordering = ['-fecha_solicitud']

# ProductoTerminado - Consultas por depósito y categoría
class ProductoTerminado(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'deposito']),
            models.Index(fields=['empresa', 'categoria']),
            models.Index(fields=['deposito', 'categoria']),
        ]
        ordering = ['descripcion']

# Insumo - Consultas por depósito y categoría
class Insumo(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'deposito']),
            models.Index(fields=['empresa', 'categoria']),
            models.Index(fields=['deposito', 'categoria']),
        ]
        ordering = ['descripcion']

# StockInsumo - Ya tiene unique_together, agregar índice empresa
class StockInsumo(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa']),
        ]

# StockProductoTerminado - Ya tiene unique_together, agregar índice empresa
class StockProductoTerminado(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa']),
        ]

# MovimientoStock - Consultas por fecha y tipo
class MovimientoStock(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'fecha']),
            models.Index(fields=['empresa', 'tipo']),
            models.Index(fields=['deposito_origen', 'fecha']),
            models.Index(fields=['deposito_destino', 'fecha']),
        ]
        ordering = ['-fecha']

# Cliente - Consultas por nombre
class Cliente(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'nombre']),
        ]
        ordering = ['nombre']

# Proveedor - Consultas por nombre
class Proveedor(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'nombre']),
        ]
        ordering = ['nombre']

# Fabricante - Consultas por nombre
class Fabricante(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'nombre']),
        ]
        ordering = ['nombre']

# ItemOrdenVenta - Consultas por orden_venta
class ItemOrdenVenta(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['orden_venta']),
        ]

# LoteProductoTerminado - Consultas por OP y producto
class LoteProductoTerminado(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa', 'op_asociada']),
            models.Index(fields=['empresa', 'producto']),
            models.Index(fields=['enviado']),
        ]
        ordering = ['-fecha_creacion']

# HistorialOV - Consultas por orden_venta y fecha
class HistorialOV(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['orden_venta', 'fecha_evento']),
        ]
        # Ya tiene ordering = ['-fecha_evento']

# ComponenteProducto - Consultas por producto_terminado
class ComponenteProducto(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['producto_terminado']),
        ]

# OfertaProveedor - Consultas por insumo y proveedor
class OfertaProveedor(EmpresaScopedModel):
    class Meta:
        indexes = [
            models.Index(fields=['empresa']),
        ]
        # Ya tiene ordering = ['insumo__descripcion', 'proveedor__nombre']
```

---

## 📊 Beneficios Esperados

| Consulta | Antes | Después |
|----------|-------|---------|
| OVs por estado | Full scan | Index seek |
| OCs por depósito | Full scan | Index seek |
| Productos por categoría | Full scan | Index seek |
| Movimientos por fecha | Full scan | Index seek |
| Stock por empresa | Full scan | Index seek |

---

## 📋 LOG DE IMPLEMENTACIÓN

### Fecha: 14 de enero de 2026

#### ✅ Paso 1: Agregar índices a modelos
- [x] OrdenVenta - 3 índices (empresa+estado, empresa+fecha_creacion, estado+fecha_creacion)
- [x] Orden (OC) - 4 índices (empresa+estado, empresa+deposito, estado+fecha_creacion, proveedor+estado)
- [x] OrdenProduccion - 4 índices (empresa+estado_op, producto+estado_op, orden_venta_origen, empresa+fecha_solicitud)
- [x] ProductoTerminado - 3 índices (empresa+deposito, empresa+categoria, deposito+categoria)
- [x] Insumo - 3 índices (empresa+deposito, empresa+categoria, deposito+categoria)
- [x] StockInsumo - 2 índices (empresa, insumo)
- [x] StockProductoTerminado - 2 índices (empresa, producto)
- [x] MovimientoStock - 4 índices (empresa+fecha, empresa+tipo, deposito_origen+fecha, deposito_destino+fecha)
- [x] Cliente - 1 índice (empresa+nombre)
- [x] Proveedor - 1 índice (empresa+nombre)
- [x] Fabricante - 1 índice (empresa+nombre)
- [x] ItemOrdenVenta - 2 índices (orden_venta, empresa)
- [x] LoteProductoTerminado - 3 índices (empresa+op_asociada, empresa+producto, enviado)
- [x] ComponenteProducto - 2 índices (producto_terminado, empresa)
- [x] OfertaProveedor - 3 índices (empresa, insumo, proveedor)
- [x] HistorialOV - 2 índices (orden_venta+fecha_evento, empresa)
- [x] Reportes - 3 índices (empresa+resuelto, empresa+fecha, orden_produccion_asociada)

**Total: 43 índices creados**

#### ✅ Paso 2: Agregar ordering por defecto
- [x] OrdenVenta: `-fecha_creacion`
- [x] Orden: `-fecha_creacion`
- [x] OrdenProduccion: `-fecha_solicitud`
- [x] ProductoTerminado: `descripcion`
- [x] Insumo: `descripcion`
- [x] MovimientoStock: `-fecha`
- [x] Cliente: `nombre`
- [x] Proveedor: `nombre`
- [x] Fabricante: `nombre`
- [x] LoteProductoTerminado: `-fecha_creacion`
- [x] Reportes: `-fecha`

#### ✅ Paso 3: Crear y aplicar migración
```bash
$ python manage.py makemigrations --name "add_performance_indexes_and_ordering"
Migrations for 'App_LUMINOVA':
  App_LUMINOVA/migrations/0038_add_performance_indexes_and_ordering.py
    ~ Change Meta options on 14 models
    + Create 43 indexes

$ python manage.py migrate
Operations to perform:
  Apply all migrations: App_LUMINOVA, admin, auth, authtoken, contenttypes, sessions
Running migrations:
  Applying App_LUMINOVA.0038_add_performance_indexes_and_ordering... OK
```

#### ✅ Paso 4: Verificación
```bash
$ python manage.py check
System check identified no issues (0 silenced)
```

---

**Fase 3 completada**: 14 de enero de 2026  
**Estado**: ✅ COMPLETADO - 43 índices de performance agregados
