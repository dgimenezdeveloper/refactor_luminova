# Solución: Filtrado Automático por Empresa

## Problema Identificado

El sistema muestra datos mezclados de diferentes empresas porque las queries NO filtran por empresa automáticamente.

## Soluciones Implementadas

### 1. Dashboard Principal ( COMPLETADO)
**Archivo**: `App_LUMINOVA/views_auth.py`

**Cambios**:
-  Filtrado de depósitos por empresa
-  OPs con problemas filtradas
-  Solicitudes de insumos filtradas
-  OCs para aprobar filtradas
-  Stock crítico filtrado
-  Rendimiento de producción filtrado
-  Actividad reciente filtrada (OV, OP, Reportes)

### 2. Selector de Depósitos ( COMPLETADO)
**Archivo**: `App_LUMINOVA/views_deposito.py`

**Cambios**:
-  Lista de depósitos filtrada por empresa
-  Validación de acceso mejorada
-  Dashboard de depósito con contadores filtrados

### 3. Usuario chef_admin ( COMPLETADO)
**Cambios aplicados via shell**:
-  Perfil asignado a "Sabores del Valle"
-  Grupos: Depósito, administrador

##  PENDIENTE: Filtrado Global

### Áreas que NECESITAN filtrado por empresa:

#### A. Vistas de Ventas (`views_ventas.py`)
```python
# PROBLEMA: Queries sin filtrar
OrdenVenta.objects.all()  #  Muestra TODAS las OVs
ProductoTerminado.objects.all()  #  Muestra TODOS los productos

# SOLUCIÓN NECESARIA:
depositos_empresa = Deposito.objects.filter(empresa=request.empresa_actual)
OrdenVenta.objects.filter(items_ov__producto_terminado__deposito__in=depositos_empresa)
ProductoTerminado.objects.filter(deposito__in=depositos_empresa)
```

#### B. Vistas de Compras (`views_compras.py`)
```python
# PROBLEMA
Orden.objects.filter(tipo='compra')  #  Todas las empresas

# SOLUCIÓN
Orden.objects.filter(tipo='compra', deposito__in=depositos_empresa)
```

#### C. Vistas de Producción (`views_producción.py`)
```python
# PROBLEMA
OrdenProduccion.objects.all()  #  Todas las empresas

# SOLUCIÓN
OrdenProduccion.objects.filter(producto_a_producir__deposito__in=depositos_empresa)
```

#### D. Vistas de Insumos (`views_insumos.py`)
```python
# PROBLEMA
Insumo.objects.all()  #  Todas las empresas

# SOLUCIÓN
Insumo.objects.filter(deposito__in=depositos_empresa)
```

#### E. Vistas de Productos (`views_productos.py`)
```python
# PROBLEMA
ProductoTerminado.objects.all()  #  Todas las empresas

# SOLUCIÓN
ProductoTerminado.objects.filter(deposito__in=depositos_empresa)
```

##  Solución Recomendada: Custom Managers

En lugar de modificar cada vista manualmente, crear managers personalizados:

```python
# En models.py
class EmpresaAwareManager(models.Manager):
    def for_empresa(self, empresa):
        """Filtra registros por empresa"""
        if empresa:
            depositos = Deposito.objects.filter(empresa=empresa)
            return self.filter(deposito__in=depositos)
        return self.none()

class Insumo(models.Model):
    # ... campos existentes ...
    objects = models.Manager()  # Manager por defecto
    empresa_aware = EmpresaAwareManager()  # Manager con filtro
```

**Uso en vistas**:
```python
# En lugar de:
insumos = Insumo.objects.all()

# Usar:
insumos = Insumo.empresa_aware.for_empresa(request.empresa_actual)
```

##  Plan de Acción

### Fase 1: Vistas Críticas (URGENTE) 
- [x] Dashboard principal
- [x] Selector de depósitos
- [x] Dashboard de depósitos

### Fase 2: Vistas de Listado (ALTA PRIORIDAD)
- [ ] Lista de OVs en ventas
- [ ] Lista de OCs en compras
- [ ] Lista de OPs en producción
- [ ] Lista de insumos
- [ ] Lista de productos

### Fase 3: Vistas de Creación/Edición (MEDIA PRIORIDAD)
- [ ] Crear/Editar OV
- [ ] Crear/Editar OC
- [ ] Crear/Editar OP
- [ ] Crear/Editar Insumo
- [ ] Crear/Editar Producto

### Fase 4: Reportes y Analytics (BAJA PRIORIDAD)
- [ ] Reportes de producción
- [ ] Reportes de ventas
- [ ] Reportes de stock

##  Principios de Aislamiento

1. **Cada empresa es un ecosistema completo**
   - Datos completamente separados
   - No hay visibilidad cruzada (excepto superusuario explícitamente)

2. **Filtrado por Depósito -> Empresa**
   - Todo objeto con FK a Deposito se filtra por empresa
   - Deposito tiene FK a Empresa

3. **Middleware garantiza empresa_actual**
   - `request.empresa_actual` siempre disponible
   - Usuarios sin perfil no pueden operar

##  Estado Actual

- Dashboard: 100% filtrado
- Depósitos: 100% filtrado
- Ventas: 0% filtrado 
- Compras: 0% filtrado 
- Producción: 0% filtrado 
- Insumos: 0% filtrado 
- Productos: 0% filtrado 

##  Próximos Pasos Inmediatos

1. Crear helper function para obtener queryset filtrado
2. Aplicar a vistas de listado más usadas
3. Testing exhaustivo con ambas empresas
4. Considerar custom managers para v2.0

---

**Última actualización**: 27 nov 2025
**Estado**: Dashboard funcional, resto pendiente
