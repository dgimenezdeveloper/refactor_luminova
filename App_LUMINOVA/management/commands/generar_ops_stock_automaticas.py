from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from App_LUMINOVA.models import ProductoTerminado, OrdenProduccion, EstadoOrden
from App_LUMINOVA.services.document_services import generar_siguiente_numero_documento
from App_LUMINOVA.utils import annotate_producto_stock


class Command(BaseCommand):
    help = 'Genera automáticamente OPs para productos que necesiten reposición de stock'

    def add_arguments(self, parser):
        parser.add_argument(
            '--deposito-id',
            type=int,
            help='ID del depósito específico para procesar (opcional)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la operación sin crear OPs reales',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la creación incluso si ya existen OPs pendientes para el producto',
        )

    def handle(self, *args, **options):
        deposito_id = options.get('deposito_id')
        dry_run = options.get('dry_run')
        force = options.get('force')

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[SIMULACIÓN] ' if dry_run else ''}Iniciando generación automática de OPs para stock..."
            )
        )

        # Filtrar productos que necesiten reposición
        # Usamos annotate_producto_stock porque 'stock' ahora es propiedad calculada
        productos_base = ProductoTerminado.objects.filter(
            produccion_para_stock_activa=True,
            stock_minimo__gt=0
        )
        productos_query = annotate_producto_stock(productos_base).filter(
            stock_calculado__lte=F('stock_minimo')
        )

        if deposito_id:
            productos_query = productos_query.filter(deposito_id=deposito_id)
            self.stdout.write(f"Filtrando por depósito ID: {deposito_id}")

        productos_necesitan_reposicion = productos_query.select_related('deposito')

        if not productos_necesitan_reposicion.exists():
            self.stdout.write(
                self.style.WARNING("No se encontraron productos que necesiten reposición.")
            )
            return

        self.stdout.write(f"Productos encontrados que necesitan reposición: {productos_necesitan_reposicion.count()}")

        ops_creadas = 0
        ops_omitidas = 0
        errores = 0

        for producto in productos_necesitan_reposicion:
            try:
                # Verificar si ya existe una OP activa para este producto (si no es --force)
                if not force:
                    op_existente = OrdenProduccion.objects.filter(
                        tipo_op="STOCK",
                        producto_a_producir=producto
                    ).exclude(
                        estado_op__nombre__in=["Completada", "Cancelada"]
                    ).exists()

                    if op_existente:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  - {producto.descripcion}: Ya existe OP activa, omitiendo..."
                            )
                        )
                        ops_omitidas += 1
                        continue

                # Calcular cantidad a producir
                cantidad_a_producir = producto.cantidad_a_producir_para_stock()
                
                if cantidad_a_producir <= 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  - {producto.descripcion}: Cantidad calculada <= 0, omitiendo..."
                        )
                    )
                    ops_omitidas += 1
                    continue

                if dry_run:
                    stock_actual = getattr(producto, 'stock_calculado', 0)
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  - [SIMULACIÓN] {producto.descripcion}: "
                            f"Se crearían {cantidad_a_producir} unidades "
                            f"(Stock: {stock_actual}, Objetivo: {producto.stock_objetivo})"
                        )
                    )
                    ops_creadas += 1
                else:
                    # Crear la OP
                    with transaction.atomic():
                        numero_op = generar_siguiente_numero_documento(OrdenProduccion, 'OP', 'numero_op')
                        estado_inicial = EstadoOrden.objects.filter(nombre="Pendiente").first()
                        stock_actual = getattr(producto, 'stock_calculado', 0)

                        op = OrdenProduccion.objects.create(
                            numero_op=numero_op,
                            tipo_op="STOCK",
                            producto_a_producir=producto,
                            cantidad_a_producir=cantidad_a_producir,
                            estado_op=estado_inicial,
                            notas=f"OP generada automáticamente para reposición de stock el {timezone.now().strftime('%d/%m/%Y %H:%M')}. "
                                  f"Stock actual: {stock_actual}, Stock mínimo: {producto.stock_minimo}, "
                                  f"Stock objetivo: {producto.stock_objetivo}."
                        )

                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ {producto.descripcion}: OP {op.numero_op} creada "
                                f"({cantidad_a_producir} unidades)"
                            )
                        )
                        ops_creadas += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Error con {producto.descripcion}: {str(e)}"
                    )
                )
                errores += 1

        # Resumen final
        self.stdout.write("\n" + "="*50)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'[SIMULACIÓN] ' if dry_run else ''}Resumen de la operación:"
            )
        )
        self.stdout.write(f"  - OPs {'simuladas' if dry_run else 'creadas'}: {ops_creadas}")
        self.stdout.write(f"  - Productos omitidos: {ops_omitidas}")
        if errores > 0:
            self.stdout.write(self.style.ERROR(f"  - Errores: {errores}"))

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nEsta fue una simulación. Use el comando sin --dry-run para crear las OPs realmente."
                )
            )
