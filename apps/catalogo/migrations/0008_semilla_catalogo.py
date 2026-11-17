"""Siembra de prueba: categorías, marcas, productos y presentaciones de data/demo/ (ADR-0023).

- Solo si DEBUG=True o SEMBRAR_DATOS_PRUEBA=True (en producción no siembra por defecto).
- Idempotente por clave natural: no choca con quien ya corrió `cargar_datos_prueba`.
- La lógica vive en `apps/catalogo/semilla.py` (la misma de `cargar_datos_prueba`) y usa los
  modelos históricos (`apps.get_model`).
- Reversa: borra por clave natural lo que ningún otro dato usa.
"""

from django.db import migrations

from apps.catalogo import semilla
from core.semilla import Resumen, avisar, directorio_por_defecto, sembrar_datos_activo


def sembrar(apps, schema_editor):
    if not sembrar_datos_activo():
        return
    resumen = Resumen()
    semilla.sembrar(apps, directorio=directorio_por_defecto(), resumen=resumen)
    for aviso in resumen.avisos:
        avisar(aviso)
    avisar(f"Catálogo de prueba: {resumen.texto()}.")


def revertir(apps, schema_editor):
    if sembrar_datos_activo():
        semilla.revertir(apps, directorio=directorio_por_defecto())


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0007_activos")]

    operations = [migrations.RunPython(sembrar, revertir)]
