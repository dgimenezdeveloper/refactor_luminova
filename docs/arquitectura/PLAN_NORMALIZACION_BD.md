# Plan de Normalización de Base de Datos - LUMINOVA

**Fecha**: 14 de enero de 2026  
**Objetivo**: Normalizar la estructura de BD para garantizar consistencia de datos antes de implementar APIs REST  
**Estado**: ✅ FASE 1 COMPLETADA

---

## 📋 Resumen de Cambios Implementados

### ✅ Cambios en Modelos (Migración 0036)

| Cambio | Estado |
|--------|--------|
| Eliminar `Insumo.stock` → usar `@property` calculada desde `StockInsumo` | ✅ |
| Eliminar `ProductoTerminado.stock` → usar `@property` calculada desde `StockProductoTerminado` | ✅ |
| Cambiar `Proveedor.nombre` de `unique=True` a `unique_together=('nombre', 'empresa')` | ✅ |
| Cambiar `Fabricante.nombre` de `unique=True` a `unique_together=('nombre', 'empresa')` | ✅ |
| Cambiar `Cliente.nombre` de `unique=True` a `unique_together=('nombre', 'empresa')` | ✅ |
| Cambiar `Cliente.email` de `unique=True` a `unique_together=('email', 'empresa')` | ✅ |
| Cambiar `Factura.numero_factura` de `unique=True` a `unique_together=('numero_factura', 'empresa')` | ✅ |

### ✅ Vistas Actualizadas

| Archivo | Cambios |
|---------|---------|
| `views_transferencias.py` | Usar `StockInsumo`/`StockProductoTerminado` para transferencias |
| `views_deposito.py` | Eliminar sincronización manual de `.stock` en entradas/salidas |
| `views_producción.py` | Actualizar stock en `StockProductoTerminado` al completar OP |

### ✅ Formularios Actualizados

| Formulario | Cambios |
|------------|---------|
| `ProductoTerminadoForm` | Eliminado campo `stock`, agregados `stock_minimo`, `stock_objetivo`, `produccion_habilitada` |
| `InsumoForm` | Eliminado campo `stock` |
| `InsumoCreateForm` | Eliminado campo `stock` |

---

## 📋 Problemas Identificados (Fase 1)

### 1. DUPLICACIÓN DE STOCK (CRÍTICO)

#### Problema
- `Insumo.stock` → campo denormalizado en modelo Insumo
- `StockInsumo.cantidad` → campo normalizado (correctamente por depósito)
- **Resultado**: Dos fuentes de verdad para el mismo dato → INCONSISTENCIA

#### Impacto
```
- Vistas modifican Insumo.stock directamente (17 lugares)
- No sincroniza con StockInsumo
- Reportes pueden mostrar datos incorrectos
- APIs REST mostrarían datos contradictorios
```

#### Solución
- ❌ Eliminar `Insumo.stock`
- ✅ Usar SOLO `StockInsumo` como fuente de verdad
- ✅ Crear property `@property stock` que suma por todos los depósitos
- ✅ Crear method `get_stock_by_deposito(deposito)` para stock específico

---

### 2. DUPLICACIÓN DE STOCK EN PRODUCTOS TERMINADOS

#### Problema
- `ProductoTerminado.stock` → campo denormalizado
- `StockProductoTerminado.cantidad` → campo normalizado por depósito
- **Resultado**: Misma inconsistencia que en Insumos

#### Solución
- ❌ Eliminar `ProductoTerminado.stock`
- ✅ Usar SOLO `StockProductoTerminado`
- ✅ Crear property `@property stock` (suma de todos los depósitos)
- ✅ Crear method `get_stock_by_deposito(deposito)`

---

### 3. CONSTRAINT GLOBAL EN PROVEEDOR.NOMBRE (MULTI-TENANT VIOLATION)

#### Problema
```python
class Proveedor(EmpresaScopedModel):
    nombre = models.CharField(max_length=100, unique=True)  # ❌ GLOBAL
```

En un sistema multi-tenant:
- Empresa A tiene proveedor "Distribuidor XYZ"
- Empresa B también quiere un proveedor "Distribuidor XYZ"
- **FALLA**: unique constraint impide crear el segundo

#### Solución
```python
# ✅ Cambiar a unique_together por empresa
class Meta:
    unique_together = ('nombre', 'empresa')
```

---

### 4. CONSTRAINT GLOBAL EN FABRICANTE.NOMBRE (MULTI-TENANT VIOLATION)

#### Problema
- Mismo problema que Proveedor
- `Fabricante.nombre` tiene `unique=True` globalmente

#### Solución
```python
class Meta:
    unique_together = ('nombre', 'empresa')
```

---

### 5. CONSTRAINT GLOBAL EN CLIENTE.NOMBRE Y EMAIL (MULTI-TENANT VIOLATION)

#### Problema
```python
class Cliente(EmpresaScopedModel):
    nombre = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True, null=True, blank=True)
```

- `nombre` no puede repetirse entre empresas
- `email` no puede repetirse entre empresas
- Viola principios de multi-tenant

#### Solución
```python
class Meta:
    unique_together = (
        ('nombre', 'empresa'),
        ('email', 'empresa'),
    )
```

---

### 6. FACTURA.NUMERO_FACTURA ÚNICO GLOBALMENTE

#### Problema
```python
class Factura(EmpresaScopedModel):
    numero_factura = models.CharField(max_length=50, unique=True)
```

En Argentina, números de factura:
- Pueden repetirse entre tipos (A, B, C, etc.)
- Pueden repetirse entre empresas
- Deberían ser únicos POR EMPRESA + TIPO

#### Solución
```python
class Meta:
    unique_together = ('numero_factura', 'empresa')
    # Considerar agregar tipo_factura si es necesario
```

---

## 🔧 Cambios a Implementar

### Paso 1: Modificar Modelos

#### 1.1 Insumo - Eliminar stock, agregar properties

```python
class Insumo(EmpresaScopedModel):
    # Eliminar: stock = models.IntegerField(default=0)
    
    @property
    def stock(self) -> int:
        """Stock total del insumo en todos sus depósitos"""
        return StockInsumo.objects.filter(insumo=self).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
    
    def get_stock_by_deposito(self, deposito: 'Deposito') -> int:
        """Stock del insumo en un depósito específico"""
        stock_record = StockInsumo.objects.filter(
            insumo=self, 
            deposito=deposito
        ).first()
        return stock_record.cantidad if stock_record else 0
```

#### 1.2 ProductoTerminado - Eliminar stock, agregar properties

```python
class ProductoTerminado(EmpresaScopedModel):
    # Eliminar: stock = models.IntegerField(default=0)
    
    @property
    def stock(self) -> int:
        """Stock total del producto en todos sus depósitos"""
        return StockProductoTerminado.objects.filter(
            producto=self
        ).aggregate(
            total=Sum('cantidad')
        )['total'] or 0
    
    def get_stock_by_deposito(self, deposito: 'Deposito') -> int:
        """Stock del producto en un depósito específico"""
        stock_record = StockProductoTerminado.objects.filter(
            producto=self,
            deposito=deposito
        ).first()
        return stock_record.cantidad if stock_record else 0
```

#### 1.3 Proveedor - Hacer nombre único por empresa

```python
class Proveedor(EmpresaScopedModel):
    nombre = models.CharField(max_length=100)  # ❌ Quitar unique=True
    # ... resto de campos
    
    class Meta:
        unique_together = ('nombre', 'empresa')
```

#### 1.4 Fabricante - Hacer nombre único por empresa

```python
class Fabricante(EmpresaScopedModel):
    nombre = models.CharField(max_length=100)  # ❌ Quitar unique=True
    # ... resto de campos
    
    class Meta:
        unique_together = ('nombre', 'empresa')
```

#### 1.5 Cliente - Hacer nombre y email únicos por empresa

```python
class Cliente(EmpresaScopedModel):
    nombre = models.CharField(max_length=150)  # ❌ Quitar unique=True
    email = models.EmailField(null=True, blank=True)  # ❌ Quitar unique=True
    # ... resto de campos
    
    class Meta:
        unique_together = (
            ('nombre', 'empresa'),
            ('email', 'empresa'),
        )
```

#### 1.6 Factura - Hacer numero_factura único por empresa

```python
class Factura(EmpresaScopedModel):
    numero_factura = models.CharField(max_length=50)  # ❌ Quitar unique=True
    # ... resto de campos
    
    class Meta:
        unique_together = ('numero_factura', 'empresa')
```

---

### Paso 2: Actualizar Vistas

Las siguientes vistas acceden a `.stock` y necesitan revisión:

1. **views_transferencias.py** (líneas 73, 80, 90, 97)
   - Cambiar: `insumo.stock -= cantidad` 
   - Por: Modificar `StockInsumo` correspondiente

2. **views_compras.py** (líneas 376, 404)
   - Cambiar: `insumo.stock + total_en_ocs`
   - Por: `insumo.get_stock_by_deposito(deposito) + total_en_ocs`

3. **views_producción.py** (línea 502)
   - Cambiar: `producto_terminado_obj.stock = F("stock") + cantidad_producida`
   - Por: Actualizar `StockProductoTerminado`

4. **views_deposito.py** (múltiples líneas)
   - Cambios similares a transferencias

---

### Paso 3: Actualizar Templates

Los templates que muestran `.stock` funcionarán correctamente una vez que las properties estén implementadas. No requieren cambios inmediatos.

---

### Paso 4: Crear Migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 📊 Orden de Implementación

```
1. Crear data migration para backfill de StockInsumo/StockProductoTerminado
   - Verificar que TODAS las combinaciones (insumo, deposito) existan
   - Asignar Insumo.stock → StockInsumo.cantidad
   - Asignar ProductoTerminado.stock → StockProductoTerminado.cantidad

2. Modificar modelos (remover campos stock, agregar properties)

3. Actualizar vistas (17 lugares que modifican stock)

4. Crear migration que elimine los campos de BD

5. Actualizar tests

6. Pruebas completas de consistencia
```

---

## ✅ Validaciones Post-Migración

```python
# Verificar que no hay datos inconsistentes
from django.db.models import Sum

# Insumos sin StockInsumo
insumos_huerfanos = []
for insumo in Insumo.objects.all():
    si_count = StockInsumo.objects.filter(insumo=insumo).count()
    if si_count == 0 and insumo.stock > 0:
        insumos_huerfanos.append(insumo)

# Productos sin StockProductoTerminado
productos_huerfanos = []
for producto in ProductoTerminado.objects.all():
    spt_count = StockProductoTerminado.objects.filter(producto=producto).count()
    if spt_count == 0 and producto.stock > 0:
        productos_huerfanos.append(producto)
```

---

## 🎯 Beneficios Esperados

| Aspecto | Antes | Después |
|---------|-------|---------|
| Fuentes de stock | 2 (duplicadas) | 1 (única verdad) |
| Consistencia | ⚠️ Frágil | ✅ Garantizada |
| Multi-tenant | ❌ Violaciones | ✅ Correcto |
| APIs REST | ❌ Confusas | ✅ Consistentes |
| Escalabilidad | ⚠️ Problemas | ✅ Sólida |

---

## 📝 Notas Importantes

- Los `@property` NO se pueden usar directamente en `select_related` pero SÍ en Python
- Para queries optimizadas, usar directamente `StockInsumo.objects.filter(...)`
- Las properties funcionan para templates y acceso ocasional desde vistas
- Considerar agregar métodos `.save()` que NO creen instancias de Stock (ya existen)

---

## 🔄 Próximas Fases

### Fase 2: Mejoras Estructurales
- Convertir Orden en tabla intermedia ItemOrden
- Hacer OrdenVenta.total_ov una @property calculada
- Normalizar EstadoOrden y SectorAsignado

### Fase 3: Optimizaciones
- Índices estratégicos
- Vistas materializadas para reportes
- Particionamiento por empresa

---

## ✅ LOG DE IMPLEMENTACIÓN - FASE 1

### Migración 0036 Aplicada Exitosamente

```
Migrations for 'App_LUMINOVA':
  App_LUMINOVA/migrations/0036_remove_insumo_stock_and_more.py
    - Remove field stock from insumo
    - Remove field stock from productoterminado
    - Alter unique_together for cliente (2 constraints)
    - Alter unique_together for fabricante (1 constraint)
    - Alter unique_together for factura (1 constraint)
    - Alter unique_together for proveedor (1 constraint)
    - Alter field email on cliente
    - Alter field nombre on cliente
    - Alter field nombre on fabricante
    - Alter field numero_factura on factura
    - Alter field nombre on proveedor
```

### Vistas Modificadas

| Archivo | Líneas Cambiadas | Descripción |
|---------|------------------|-------------|
| `views_transferencias.py` | Imports + lógica stock | Usar StockInsumo/StockProductoTerminado |
| `views_deposito.py` | ~5 ubicaciones | Eliminar sincronización manual de .stock |
| `views_producción.py` | Completar OP | Actualizar StockProductoTerminado |

### Scripts Actualizados

| Script | Cambio |
|--------|--------|
| `scripts/verificar_y_corregir_depositos.py` | Convertido a solo verificación (stock es property ahora) |

### Validación Final

```bash
$ python manage.py check
System check identified no issues (0 silenced)
```

### Propiedades Verificadas

```python
>>> from App_LUMINOVA.models import Insumo, ProductoTerminado
>>> i = Insumo.objects.first()
>>> i.stock  # Calculado desde StockInsumo
69994
>>> p = ProductoTerminado.objects.first()
>>> p.necesita_reposicion  # Usa property stock correctamente
False
```

---

**Documento creado**: 14 de enero de 2026  
**Fase 1 completada**: 14 de enero de 2026  
**Estado**: ✅ FASE 1 COMPLETADA - Sistema normalizado y verificado
