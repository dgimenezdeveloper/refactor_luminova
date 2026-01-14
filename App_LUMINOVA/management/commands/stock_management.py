from django.core.management.base import BaseCommand
from django.db.models import F
from App_LUMINOVA.models import ProductoTerminado, OrdenProduccion
from App_LUMINOVA.utils import annotate_producto_stock


class Command(BaseCommand):
    help = 'Gestiona tareas relacionadas con producción para stock'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['configurar_stock', 'reporte_stock', 'sugerencias'],
            help='Acción a realizar'
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Resetear configuración de stock existente',
        )

    def handle(self, *args, **options):
        action = options['action']
        
        if action == 'configurar_stock':
            self.configurar_stock(reset=options.get('reset', False))
        elif action == 'reporte_stock':
            self.reporte_stock()
        elif action == 'sugerencias':
            self.mostrar_sugerencias()

    def configurar_stock(self, reset=False):
        """Configura niveles de stock para productos"""
        self.stdout.write(self.style.SUCCESS('Configurando niveles de stock...'))
        
        # Usamos annotate_producto_stock porque 'stock' ahora es propiedad calculada
        productos = annotate_producto_stock(ProductoTerminado.objects.all())
        productos_actualizados = 0
        
        for producto in productos:
            # Solo actualizar si reset=True o si no tienen configuración
            if reset or (producto.stock_minimo == 0 and producto.stock_objetivo == 0):
                stock_actual = getattr(producto, 'stock_calculado', 0)
                
                if stock_actual > 0:
                    # Configuración inteligente basada en stock actual
                    if stock_actual >= 100:
                        stock_minimo = max(20, int(stock_actual * 0.15))
                        stock_objetivo = int(stock_actual * 1.3)
                    elif stock_actual >= 50:
                        stock_minimo = max(10, int(stock_actual * 0.2))
                        stock_objetivo = int(stock_actual * 1.5)
                    else:
                        stock_minimo = max(5, int(stock_actual * 0.3))
                        stock_objetivo = int(stock_actual * 2)
                else:
                    # Valores por defecto para productos sin stock
                    stock_minimo = 10
                    stock_objetivo = 50
                
                producto.stock_minimo = stock_minimo
                producto.stock_objetivo = stock_objetivo
                producto.produccion_habilitada = True
                producto.save()
                
                productos_actualizados += 1
                self.stdout.write(
                    f"✓ {producto.descripcion[:50]}... "
                    f"Min: {stock_minimo}, Obj: {stock_objetivo}"
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Configuración completada! {productos_actualizados} productos actualizados.'
            )
        )

    def reporte_stock(self):
        """Genera un reporte del estado actual del stock"""
        self.stdout.write(self.style.SUCCESS('=== REPORTE DE STOCK ==='))
        
        # Usamos annotate_producto_stock porque 'stock' ahora es propiedad calculada
        productos_qs = annotate_producto_stock(ProductoTerminado.objects.filter(produccion_habilitada=True))
        
        # Productos críticos (sin stock)
        productos_sin_stock = productos_qs.filter(stock_calculado=0)
        if productos_sin_stock.exists():
            self.stdout.write(self.style.ERROR(f'\n🔴 CRÍTICO - Sin Stock ({productos_sin_stock.count()} productos):'))
            for producto in productos_sin_stock[:10]:
                self.stdout.write(f"   - {producto.descripcion}")
        
        # Productos con stock bajo
        productos_stock_bajo = productos_qs.filter(
            stock_calculado__lte=F('stock_minimo'),
            stock_calculado__gt=0
        )
        if productos_stock_bajo.exists():
            self.stdout.write(self.style.WARNING(f'\n🟡 STOCK BAJO ({productos_stock_bajo.count()} productos):'))
            for producto in productos_stock_bajo[:10]:
                self.stdout.write(
                    f"   - {producto.descripcion}: {producto.stock_calculado}/{producto.stock_minimo}"
                )
        
        # Productos normales
        productos_normales = productos_qs.filter(
            stock_calculado__gt=F('stock_minimo'),
            stock_calculado__lte=F('stock_objetivo')
        )
        self.stdout.write(self.style.SUCCESS(f'\n🟢 STOCK NORMAL: {productos_normales.count()} productos'))
        
        # Productos con sobrestock
        productos_sobrestock = productos_qs.filter(
            stock_calculado__gt=F('stock_objetivo')
        )
        if productos_sobrestock.exists():
            self.stdout.write(self.style.HTTP_INFO(f'\n🔵 SOBRESTOCK ({productos_sobrestock.count()} productos):'))
            for producto in productos_sobrestock[:5]:
                self.stdout.write(
                    f"   - {producto.descripcion}: {producto.stock_calculado}/{producto.stock_objetivo}"
                )

    def mostrar_sugerencias(self):
        """Muestra sugerencias de producción"""
        self.stdout.write(self.style.SUCCESS('=== SUGERENCIAS DE PRODUCCIÓN ==='))
        
        # Usamos annotate_producto_stock porque 'stock' ahora es propiedad calculada
        productos_necesitan_reposicion = annotate_producto_stock(
            ProductoTerminado.objects.filter(produccion_habilitada=True)
        ).filter(
            stock_calculado__lte=F('stock_minimo')
        ).order_by('stock_calculado')
        
        if not productos_necesitan_reposicion.exists():
            self.stdout.write(self.style.SUCCESS('✅ No hay productos que necesiten reposición.'))
            return
        
        self.stdout.write(f'\n📋 Productos que necesitan reposición ({productos_necesitan_reposicion.count()}):\n')
        
        for producto in productos_necesitan_reposicion:
            # Verificar OPs activas
            ops_activas = OrdenProduccion.objects.filter(
                producto_a_producir=producto,
                tipo_orden='MTS'
            ).exclude(
                estado_op__nombre__iexact='Completada'
            ).exclude(
                estado_op__nombre__iexact='Cancelada'
            )
            
            stock_actual = getattr(producto, 'stock_calculado', 0)
            cantidad_en_produccion = sum(op.cantidad_a_producir for op in ops_activas)
            stock_proyectado = stock_actual + cantidad_en_produccion
            cantidad_sugerida = max(0, producto.stock_objetivo - stock_actual)
            
            urgencia = "CRÍTICO" if stock_actual == 0 else "URGENTE" if stock_proyectado <= producto.stock_minimo else "NORMAL"
            
            self.stdout.write(
                f"• {producto.descripcion[:40]:<40} | "
                f"Stock: {stock_actual:>3} | "
                f"Min: {producto.stock_minimo:>3} | "
                f"Obj: {producto.stock_objetivo:>3} | "
                f"Sugerido: {cantidad_sugerida:>3} | "
                f"OPs: {ops_activas.count():>1} | "
                f"{urgencia}"
            )
        
        self.stdout.write(
            self.style.WARNING(
                f'\n💡 Consejo: Use "python manage.py crearsuperusuario" para acceder al admin '
                f'y crear órdenes de producción para estos productos.'
            )
        )
