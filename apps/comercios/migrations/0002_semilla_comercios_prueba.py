"""Siembra de prueba del módulo comercial (ADR-0023).

- Solo si DEBUG=True o SEMBRAR_DATOS_PRUEBA=True, y si existe `moderador_prueba` (lo crea
  `cuentas.0006` con SEMBRAR_CUENTAS_PRUEBA o en local).
- Dos comercios verificados con precios oficiales y una promoción de cada tipo. Lógica en
  `apps/comercios/semilla.py`, con modelos históricos. No cambia datos existentes.
- Reversa: borra los perfiles sembrados (marcados) con sus precios y promociones.
"""

from django.db import migrations
from django.utils import timezone

from apps.comercios import semilla
from core.semilla import avisar, sembrar_datos_activo


def sembrar(apps, schema_editor):
    if not sembrar_datos_activo():
        return
    nuevos, avisos = semilla.sembrar(apps, ahora=timezone.now())
    for aviso in avisos:
        avisar(aviso)
    avisar(f"Comercios de prueba: {nuevos} nuevos.")


def revertir(apps, schema_editor):
    if sembrar_datos_activo():
        semilla.revertir(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("comercios", "0001_initial"),
        ("precios", "0006_merge_origen_y_semilla"),
        ("catalogo", "0008_semilla_catalogo"),
        ("establecimientos", "0004_semilla_directorio"),
        ("cuentas", "0006_semilla_cuentas_prueba"),
    ]

    operations = [migrations.RunPython(sembrar, revertir)]
