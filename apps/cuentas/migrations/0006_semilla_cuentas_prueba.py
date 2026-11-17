"""Siembra los grupos de rol (si faltan) y las cuentas de prueba (ADR-0023).

- Grupos: siempre; los que ya existen no se tocan.
- Cuentas: solo si DEBUG=True o SEMBRAR_CUENTAS_PRUEBA=True. En producción, por defecto, no se
  crea ninguna (serían cuentas con rol conocido y una contraseña compartida).
- Contraseña: os.environ["CUENTAS_PRUEBA_PASSWORD"] (el .env la carga al leer settings). Nunca
  se escribe en el código ni se imprime. Sin ella, o si no cumple los validadores, las cuentas
  nuevas quedan con contraseña inutilizable y se muestra cómo activarlas. Las cuentas que ya
  tenían contraseña la conservan.
- Lógica en `apps/cuentas/semilla.py` (la misma de `crear_cuentas_prueba`).
- Reversa: borra las cuentas de prueba sin aportes; los grupos se quedan.
"""

import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import migrations

from apps.cuentas import semilla
from apps.cuentas.domain.cuentas_prueba import VARIABLE_CONTRASENA
from core.semilla import avisar, sembrar_cuentas_activo

ACTIVARLAS = (
    f"Define {VARIABLE_CONTRASENA} y corre python manage.py crear_cuentas_prueba para activarlas."
)


def _contrasena() -> str | None:
    valor = os.environ.get(VARIABLE_CONTRASENA, "")
    if not valor.strip():
        return None
    try:
        validate_password(valor)
    except ValidationError as exc:  # el mensaje del validador nunca incluye la contraseña
        avisar(f"{VARIABLE_CONTRASENA} no cumple las reglas: " + " ".join(exc.messages))
        return None
    return valor


def sembrar(apps, schema_editor):
    semilla.asegurar_grupos(apps)
    if not sembrar_cuentas_activo():
        avisar("Cuentas de prueba: no se crean (DEBUG=False y SEMBRAR_CUENTAS_PRUEBA=False).")
        return
    contrasena = _contrasena()
    cuentas = semilla.sembrar(apps, contrasena=contrasena, fijar_en_existentes=False)
    nuevas = sum(creada for _, creada in cuentas)
    avisar(f"Cuentas de prueba: {len(cuentas)} ({nuevas} nuevas).")
    if contrasena is None:
        avisar(f"Las cuentas de prueba nuevas quedaron sin contraseña utilizable. {ACTIVARLAS}")


def revertir(apps, schema_editor):
    if sembrar_cuentas_activo():
        semilla.revertir(apps)


class Migration(migrations.Migration):
    dependencies = [
        ("cuentas", "0005_usuario_es_cuenta_prueba"),
        ("administracion", "0002_grupos_de_roles"),  # crea los grupos y sus permisos
    ]

    operations = [migrations.RunPython(sembrar, revertir)]
