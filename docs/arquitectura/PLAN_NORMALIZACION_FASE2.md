# Plan de Normalización de Base de Datos - LUMINOVA
## Fase 2: Mejoras Estructurales

**Fecha**: 14 de enero de 2026  
**Estado**: ✅ COMPLETADO  
**Prerrequisito**: [PLAN_NORMALIZACION_BD.md](PLAN_NORMALIZACION_BD.md) - Fase 1 Completada

---

## 📋 Objetivos de la Fase 2

### 1. ✅ Hacer `OrdenVenta.total_ov` una @property calculada
**Problema**: El campo `total_ov` se almacena en la BD y se actualiza manualmente, causando potenciales inconsistencias.

**Solución**: Convertir a `@property` que calcula dinámicamente desde `items_ov`.

### 2. ✅ Hacer `Orden.total_orden_compra` una @property calculada
**Problema**: Similar a OrdenVenta, el total de orden de compra se almacena y puede desincronizarse.

**Solución**: Convertir a `@property` calculada.

### 3. 🔍 Análisis de `EstadoOrden` y `SectorAsignado`

Después de revisar los modelos, encontré que:
- `EstadoOrden` y `SectorAsignado` YA están correctamente normalizados con multi-tenancy
- Tienen `unique_together = ('nombre', 'empresa')` correctamente configurado
- No requieren cambios adicionales

### 4. ❌ Normalización de ItemOrden para Orden de Compra (DESCARTADO)

Después del análisis, el modelo `Orden` (OC) tiene una estructura diferente:
- `insumo_principal` + `cantidad_principal` + `precio_unitario_compra` = un solo insumo por orden
- NO requiere tabla de items como en OV (que tiene múltiples productos)
- El diseño actual es correcto para el caso de uso

---

## 🔧 Cambios a Implementar

### Paso 1: Modificar OrdenVenta.total_ov → @property

#### Antes
```python
class OrdenVenta(EmpresaScopedModel):
    total_ov = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, verbose_name="Total OV"
    )
    
    def actualizar_total(self):
        nuevo_total = sum(item.subtotal for item in self.items_ov.all())
        if self.total_ov != nuevo_total:
            self.total_ov = nuevo_total
            self.save(update_fields=["total_ov"])
```

#### Después
```python
class OrdenVenta(EmpresaScopedModel):
    # Eliminar: total_ov = models.DecimalField(...)
    
    @property
    def total_ov(self) -> Decimal:
        """Total calculado dinámicamente desde items"""
        from django.db.models import Sum
        total = self.items_ov.aggregate(total=Sum('subtotal'))['total']
        return total or Decimal('0.00')
    
    # Eliminar: def actualizar_total(self): ...
```

### Paso 2: Modificar Orden.total_orden_compra → @property

#### Antes
```python
class Orden(EmpresaScopedModel):
    total_orden_compra = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00
    )
    
    def save(self, *args, **kwargs):
        if (self.insumo_principal and self.cantidad_principal 
            and self.precio_unitario_compra is not None):
            self.total_orden_compra = (
                self.cantidad_principal * self.precio_unitario_compra
            )
        super().save(*args, **kwargs)
```

#### Después
```python
class Orden(EmpresaScopedModel):
    # Eliminar: total_orden_compra = models.DecimalField(...)
    
    @property
    def total_orden_compra(self) -> Decimal:
        """Total calculado dinámicamente"""
        if (self.insumo_principal and self.cantidad_principal 
            and self.precio_unitario_compra is not None):
            return Decimal(self.cantidad_principal) * self.precio_unitario_compra
        return Decimal('0.00')
```

---

## 📝 Archivos a Modificar

| Archivo | Cambios |
|---------|---------|
| `models.py` | Eliminar campos, agregar @property |
| `views_ventas.py` | Eliminar llamadas a `actualizar_total()` |
| `views_compras.py` | Ajustar si hay referencias al total |
| `api/serializers.py` | Ajustar serializadores |
| Templates | Verificar que sigan funcionando (properties funcionan igual) |

---

## ⚠️ Consideraciones Importantes

### 1. Migraciones
- Se crearán migraciones para eliminar los campos
- Los datos históricos se perderán (pero son calculables)
- NO se requiere data migration ya que el cálculo es idéntico

### 2. Performance
- Las @properties calculan en cada acceso
- Para listados grandes, usar `annotate()` con `Sum()`
- Las vistas que listan muchas órdenes deben optimizarse

### 3. Compatibilidad de Templates
- Los templates seguirán funcionando igual (`{{ orden.total_ov }}`)
- Las @properties se acceden igual que campos

### 4. Compatibilidad de API
- Los serializadores deben definir el campo como `ReadOnlyField()`
- Ya está configurado correctamente en la implementación actual

---

## 📊 Orden de Implementación

```
1. ✅ Modificar OrdenVenta - agregar @property total_ov
2. ✅ Modificar Orden - agregar @property total_orden_compra  
3. ✅ Actualizar vistas que llaman actualizar_total()
4. ✅ Verificar/actualizar serializadores API
5. ✅ Crear migración para eliminar campos
6. ✅ Ejecutar tests
7. ✅ Verificar funcionamiento en navegador
```

---

## 📋 LOG DE IMPLEMENTACIÓN

### Fecha: 14 de enero de 2026

#### ✅ Paso 1: Modificar OrdenVenta.total_ov → @property
- Eliminado campo `DecimalField` de `OrdenVenta`
- Agregada `@property total_ov` que calcula desde `items_ov.aggregate(Sum('subtotal'))`
- Eliminado método `actualizar_total()` (ya no necesario)

#### ✅ Paso 2: Modificar Orden.total_orden_compra → @property
- Eliminado campo `DecimalField` de `Orden`
- Agregada `@property total_orden_compra` que calcula desde `cantidad_principal * precio_unitario_compra`
- Eliminada lógica de cálculo en `save()`

#### ✅ Paso 3: Actualizar vistas
- Eliminada llamada a `actualizar_total()` en `views_ventas.py` (línea 648)
- Los templates siguen funcionando sin cambios (properties se acceden igual)

#### ✅ Paso 4: Actualizar serializadores API
- `OrdenVentaListSerializer`: agregado `SerializerMethodField` para `total_ov`
- `OrdenVentaSerializer`: agregado `SerializerMethodField` para `total_ov`
- `OrdenCompraListSerializer`: agregado `SerializerMethodField` para `total_orden_compra`
- `OrdenCompraSerializer`: agregado `SerializerMethodField` para `total_orden_compra`
- **Type hints**: Agregados `-> str` a todos los métodos `get_total_*` para eliminar warnings de drf-spectacular

#### ✅ Paso 5: Crear y aplicar migración
```bash
$ python manage.py makemigrations --name "remove_total_ov_and_total_orden_compra_fields"
Migrations for 'App_LUMINOVA':
  App_LUMINOVA/migrations/0037_remove_total_ov_and_total_orden_compra_fields.py
    - Remove field total_orden_compra from orden
    - Remove field total_ov from ordenventa

$ python manage.py migrate
Operations to perform:
  Apply all migrations: App_LUMINOVA, admin, auth, authtoken, contenttypes, sessions
Running migrations:
  Applying App_LUMINOVA.0037_remove_total_ov_and_total_orden_compra_fields... OK
```

#### ✅ Paso 6: Verificación
```bash
$ python manage.py check
System check identified no issues (0 silenced)
```

---

## 📊 Beneficios Obtenidos

| Aspecto | Antes | Después |
|---------|-------|---------|
| Fuentes de totales | 2 (campo + cálculo) | 1 (solo cálculo) |
| Consistencia | ⚠️ Posible desincronización | ✅ Siempre consistente |
| Mantenimiento | ⚠️ Requiere actualizar_total() | ✅ Automático |
| Campos en BD | 2 campos DecimalField | 0 campos (calculados) |

---

## 📁 Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `App_LUMINOVA/models.py` | Eliminados campos, agregadas @property |
| `App_LUMINOVA/views_ventas.py` | Eliminada llamada a actualizar_total() |
| `App_LUMINOVA/api/serializers.py` | Agregados SerializerMethodField |
| `App_LUMINOVA/migrations/0037_*.py` | Migración para eliminar campos |

---

**Fase 2 completada**: 14 de enero de 2026  
**Estado**: ✅ COMPLETADO - Totales ahora son propiedades calculadas
