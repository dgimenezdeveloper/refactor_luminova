#!/usr/bin/env python
"""
Script de verificación de integridad multi-tenancy para LUMINOVA.
Verifica que todos los registros tengan empresa asignada y que los filtros funcionen correctamente.

Uso:
    python verificar_multitenancy.py
"""
import os
import sys

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Proyecto_LUMINOVA.settings')

import django
django.setup()

from django.db.models import Count, Q, F
from App_LUMINOVA.models import (
    Empresa, Deposito, CategoriaInsumo, CategoriaProductoTerminado,
    Insumo, ProductoTerminado, Cliente, Proveedor, Fabricante,
    OrdenVenta, OrdenProduccion, Orden, StockInsumo, StockProductoTerminado,
    MovimientoStock, NotificacionSistema, ItemOrdenVenta, Factura,
    OfertaProveedor, ComponenteProducto, LoteProductoTerminado, HistorialOV,
    Reportes, UsuarioDeposito, EstadoOrden, SectorAsignado, AuditoriaAcceso,
    PerfilUsuario, RolEmpresa
)


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title):
    print(f"\n--- {title} ---")


def verificar_modelos_con_empresa():
    """Verifica que todos los modelos multi-tenant tengan empresa asignada."""
    print_header("VERIFICACIÓN DE MODELOS MULTI-TENANT")
    
    modelos = [
        ('Deposito', Deposito, True),
        ('CategoriaInsumo', CategoriaInsumo, True),
        ('CategoriaProductoTerminado', CategoriaProductoTerminado, True),
        ('Insumo', Insumo, True),
        ('ProductoTerminado', ProductoTerminado, True),
        ('Cliente', Cliente, True),
        ('Proveedor', Proveedor, True),
        ('Fabricante', Fabricante, True),
        ('OrdenVenta', OrdenVenta, True),
        ('OrdenProduccion', OrdenProduccion, True),
        ('Orden', Orden, True),
        ('StockInsumo', StockInsumo, True),
        ('StockProductoTerminado', StockProductoTerminado, True),
        ('MovimientoStock', MovimientoStock, True),
        ('NotificacionSistema', NotificacionSistema, True),
        ('ItemOrdenVenta', ItemOrdenVenta, True),
        ('Factura', Factura, True),
        ('OfertaProveedor', OfertaProveedor, True),
        ('ComponenteProducto', ComponenteProducto, True),
        ('LoteProductoTerminado', LoteProductoTerminado, True),
        ('HistorialOV', HistorialOV, True),
        ('Reportes', Reportes, True),
        ('UsuarioDeposito', UsuarioDeposito, True),
        ('EstadoOrden', EstadoOrden, True),
        ('SectorAsignado', SectorAsignado, True),
        ('AuditoriaAcceso', AuditoriaAcceso, True),
        ('PerfilUsuario', PerfilUsuario, True),
        ('RolEmpresa', RolEmpresa, True),
    ]
    
    errores = []
    warnings = []
    
    print(f"\n{'Modelo':35} | {'Total':>8} | {'Sin Empresa':>12} | {'Estado'}")
    print("-" * 80)
    
    for nombre, modelo, debe_tener_empresa in modelos:
        tiene_empresa = any(f.name == 'empresa' for f in modelo._meta.fields)
        total = modelo.objects.count()
        sin_empresa = 0
        
        if tiene_empresa:
            sin_empresa = modelo.objects.filter(empresa__isnull=True).count()
        
        if debe_tener_empresa:
            if tiene_empresa and sin_empresa == 0:
                status = '✓ OK'
            elif tiene_empresa and sin_empresa > 0:
                status = '⚠ PENDIENTE'
                warnings.append(f"{nombre}: {sin_empresa} registros sin empresa")
            else:
                status = '✗ FALTA CAMPO'
                errores.append(f"{nombre}: No tiene campo empresa")
        else:
            status = '- N/A'
        
        print(f'{nombre:35} | {total:>8} | {sin_empresa:>12} | {status}')
    
    return errores, warnings


def verificar_consistencia_relaciones():
    """Verifica que las relaciones entre modelos sean consistentes en cuanto a empresa."""
    print_header("VERIFICACIÓN DE CONSISTENCIA DE RELACIONES")
    
    errores = []
    
    # Verificar que los depósitos de insumos coincidan con su empresa
    print_section("Insumos vs Depósitos")
    insumos_inconsistentes = Insumo.objects.exclude(
        Q(empresa__isnull=True) | Q(deposito__empresa=F('empresa'))
    ).count()
    if insumos_inconsistentes:
        errores.append(f"Hay {insumos_inconsistentes} insumos con empresa diferente a su depósito")
        print(f"⚠ {insumos_inconsistentes} insumos inconsistentes")
    else:
        print("✓ Todos los insumos tienen empresa consistente con su depósito")
    
    # Verificar OVs vs Clientes
    print_section("OrdenVenta vs Cliente")
    ovs_inconsistentes = OrdenVenta.objects.exclude(
        Q(empresa__isnull=True) | Q(cliente__empresa=F('empresa'))
    ).count()
    if ovs_inconsistentes:
        errores.append(f"Hay {ovs_inconsistentes} OVs con empresa diferente a su cliente")
        print(f"⚠ {ovs_inconsistentes} órdenes de venta inconsistentes")
    else:
        print("✓ Todas las órdenes de venta tienen empresa consistente con su cliente")
    
    # Verificar OPs vs Productos
    print_section("OrdenProduccion vs ProductoTerminado")
    ops_inconsistentes = OrdenProduccion.objects.exclude(
        Q(empresa__isnull=True) | Q(producto_a_producir__empresa=F('empresa'))
    ).count()
    if ops_inconsistentes:
        errores.append(f"Hay {ops_inconsistentes} OPs con empresa diferente a su producto")
        print(f"⚠ {ops_inconsistentes} órdenes de producción inconsistentes")
    else:
        print("✓ Todas las órdenes de producción tienen empresa consistente")
    
    # Verificar UsuarioDeposito vs Depósito
    print_section("UsuarioDeposito vs Depósito")
    ud_inconsistentes = UsuarioDeposito.objects.exclude(
        Q(empresa__isnull=True) | Q(deposito__empresa=F('empresa'))
    ).count()
    if ud_inconsistentes:
        errores.append(f"Hay {ud_inconsistentes} UsuarioDeposito con empresa diferente a su depósito")
        print(f"⚠ {ud_inconsistentes} asignaciones usuario-depósito inconsistentes")
    else:
        print("✓ Todas las asignaciones usuario-depósito tienen empresa consistente")
    
    return errores


def mostrar_distribucion_por_empresa():
    """Muestra la distribución de datos por empresa."""
    print_header("DISTRIBUCIÓN DE DATOS POR EMPRESA")
    
    empresas = Empresa.objects.filter(activa=True)
    
    for empresa in empresas:
        print(f"\n🏢 {empresa.nombre} (ID: {empresa.id})")
        print("-" * 40)
        
        stats = [
            ('Depósitos', Deposito.objects.filter(empresa=empresa).count()),
            ('Insumos', Insumo.objects.filter(empresa=empresa).count()),
            ('Productos', ProductoTerminado.objects.filter(empresa=empresa).count()),
            ('Clientes', Cliente.objects.filter(empresa=empresa).count()),
            ('Proveedores', Proveedor.objects.filter(empresa=empresa).count()),
            ('Órdenes de Venta', OrdenVenta.objects.filter(empresa=empresa).count()),
            ('Órdenes de Producción', OrdenProduccion.objects.filter(empresa=empresa).count()),
            ('Órdenes de Compra', Orden.objects.filter(empresa=empresa).count()),
            ('Usuarios asignados', PerfilUsuario.objects.filter(empresa=empresa).count()),
        ]
        
        for nombre, cantidad in stats:
            print(f"  • {nombre:25} {cantidad:>6}")


def main():
    print("\n" + "=" * 80)
    print("    VERIFICACIÓN DE INTEGRIDAD MULTI-TENANCY - LUMINOVA")
    print("    Fecha: " + str(django.utils.timezone.now().strftime('%Y-%m-%d %H:%M:%S')))
    print("=" * 80)
    
    # 1. Verificar modelos
    errores_modelos, warnings_modelos = verificar_modelos_con_empresa()
    
    # 2. Verificar consistencia
    errores_consistencia = verificar_consistencia_relaciones()
    
    # 3. Mostrar distribución
    mostrar_distribucion_por_empresa()
    
    # Resumen final
    print_header("RESUMEN DE VERIFICACIÓN")
    
    total_errores = len(errores_modelos) + len(errores_consistencia)
    total_warnings = len(warnings_modelos)
    
    if total_errores == 0 and total_warnings == 0:
        print("\n✅ SISTEMA MULTI-TENANT VERIFICADO CORRECTAMENTE")
        print("   - Todos los modelos tienen campo empresa")
        print("   - Todos los registros tienen empresa asignada")
        print("   - Las relaciones son consistentes")
        return 0
    
    if errores_modelos:
        print("\n❌ ERRORES EN MODELOS:")
        for error in errores_modelos:
            print(f"   • {error}")
    
    if errores_consistencia:
        print("\n❌ ERRORES DE CONSISTENCIA:")
        for error in errores_consistencia:
            print(f"   • {error}")
    
    if warnings_modelos:
        print("\n⚠ ADVERTENCIAS:")
        for warning in warnings_modelos:
            print(f"   • {warning}")
    
    return 1 if total_errores > 0 else 0


if __name__ == '__main__':
    sys.exit(main())
