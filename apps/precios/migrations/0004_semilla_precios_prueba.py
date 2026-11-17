"""Siembra de prueba: precios.csv, «Sigue igual», denuncias, solicitudes y el local sugerido
(ADR-0023).

- Solo si DEBUG=True o SEMBRAR_DATOS_PRUEBA=True, y si existen las cuentas de prueba (son los
  autores; las crea `cuentas.0006`).
- Precios con es_demo=True y fechas RELATIVAS: «hace N días» se calcula con timezone.now() al
  migrar. Para renovarlas después: python manage.py refrescar_precios_prueba.
- Reglas replicadas con el dominio puro: el anómalo queda «en revisión» (EC-03) y los 3 reportes
  iguales dan confianza alta.
- Idempotente por id_cliente (el mismo UUID que usa `cargar_datos_prueba`).
- Lógica en `apps/precios/semilla.py`, con modelos históricos.
- Reversa: borra los precios sembrados (con sus confirmaciones y denuncias), las solicitudes y la
  sugerencia de prueba.
"""

from django.db import migrations
from django.utils import timezone

from apps.cuentas import semilla as semilla_cuentas
from apps.cuentas.domain.cuentas_prueba import CUENTAS_PRUEBA
from apps.precios import semilla
from core.semilla import Resumen, avisar, directorio_por_defecto, sembrar_datos_activo


def sembrar(apps, schema_editor):
    if not sembrar_datos_activo():
        return
    autores = semilla_cuentas.autores(apps)
    if len(autores) < len(CUENTAS_PRUEBA):
        avisar(
            "Precios de prueba: no se cargan porque faltan las cuentas de prueba (sus autores). "
            "Active SEMBRAR_CUENTAS_PRUEBA o corra python manage.py cargar_datos_prueba."
        )
        return
    resumen = Resumen()
    semilla.sembrar(
        apps,
        directorio=directorio_por_defecto(),
        autores=autores,
        ahora=timezone.now(),
        resumen=resumen,
    )
    avisar(f"Precios de prueba: {resumen.texto()}.")


def revertir(apps, schema_editor):
    if sembrar_datos_activo():
        semilla.revertir(
            apps, directorio=directorio_por_defecto(), autores=semilla_cuentas.autores(apps)
        )


class Migration(migrations.Migration):
    dependencies = [
        ("precios", "0003_reporte_es_demo"),
        ("catalogo", "0008_semilla_catalogo"),
        ("establecimientos", "0004_semilla_directorio"),
        ("cuentas", "0006_semilla_cuentas_prueba"),
        ("moderacion", "0002_decision_moderacion"),
    ]

    operations = [migrations.RunPython(sembrar, revertir)]
