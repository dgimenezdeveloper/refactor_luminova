# Script para asignar todos los insumos sin depósito al depósito 'Luminova Central'
# Uso: python manage.py shell < asignar_insumos_a_luminova.py

from App_LUMINOVA.models import Insumo, Deposito

# Cambia el nombre si tu depósito central tiene otro nombre
NOMBRE_DEPOSITO_CENTRAL = "Luminova Central"

def main():
    try:
        deposito = Deposito.objects.get(nombre__icontains=NOMBRE_DEPOSITO_CENTRAL)
    except Deposito.DoesNotExist:
        print(f"No se encontró un depósito con nombre que contenga: {NOMBRE_DEPOSITO_CENTRAL}")
        return

    insumos_sin_deposito = Insumo.objects.filter(deposito__isnull=True)
    total = insumos_sin_deposito.count()
    if total == 0:
        print("No hay insumos sin depósito asignado.")
        return

    insumos_sin_deposito.update(deposito=deposito)
    print(f"Asignados {total} insumos al depósito '{deposito.nombre}' (ID: {deposito.id})")

if __name__ == "__main__":
    main()
