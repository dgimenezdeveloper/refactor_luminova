from productos.models import EstadoOrden

ESTADOS = [
    "Pendiente",
    "Planificada",
    "En Proceso",
    "Completada",
    "Cancelada",
    "Insumos Solicitados",
    "Insumos Recibidos",
]

def run():
    for nombre in ESTADOS:
        obj, created = EstadoOrden.objects.get_or_create(nombre=nombre)
        if created:
            print(f"Estado creado: {nombre}")
        else:
            print(f"Ya existía: {nombre}")
    print("Carga de estados finalizada.")
