"""Punto 0: cargar_demo crea accesos sin contraseñas en el código y carga precios vencidos."""

from io import StringIO

import pytest
from django.core.management import call_command

from apps.catalogo.models import Producto
from apps.comparacion.selectors import comparar_producto
from apps.cuentas.models import Usuario

pytestmark = pytest.mark.integration

CLAVE = "clave-de-prueba-solo-test"


def _cargar(*args) -> str:
    salida = StringIO()
    call_command("cargar_demo", *args, stdout=salida)
    return salida.getvalue()


def test_crea_admin_y_moderador_con_la_clave_de_entorno(db, monkeypatch):
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", CLAVE)
    monkeypatch.setenv("DEMO_PASSWORD", CLAVE)
    salida = _cargar()
    admin = Usuario.objects.get(username="admin")
    moderador = Usuario.objects.get(username="moderador_demo")
    assert admin.is_superuser and admin.check_password(CLAVE)
    assert moderador.rol == Usuario.Rol.MODERADOR and moderador.is_staff
    assert moderador.check_password(CLAVE)
    assert moderador.groups.filter(name="Moderadores").exists()
    assert CLAVE not in salida  # la clave de entorno no se imprime


def test_sin_variable_genera_una_clave_aleatoria_y_la_muestra_una_sola_vez(db, monkeypatch):
    monkeypatch.delenv("DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    primera = _cargar()
    segunda = _cargar()
    assert "Contraseña generada para admin y moderador_demo" in primera
    assert "Contraseña generada" not in segunda
    assert "no se cambió su contraseña" in segunda


def test_con_vencidos_la_comparacion_oculta_los_precios_vencidos(db, monkeypatch):
    # EC-02: 8 días reportado, 4 días perecedero y 31 días oficial no se muestran
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", CLAVE)
    monkeypatch.setenv("DEMO_PASSWORD", CLAVE)
    _cargar("--con-vencidos")
    frijol = Producto.objects.get(nombre="Frijol cargamanto")
    queso = Producto.objects.get(nombre="Queso campesino")
    assert {r.establecimiento for r in comparar_producto(frijol.pk)} == {
        "Tienda El Vecino",  # 6 días
        "Supermercado del Parque",  # oficial, 29 días
    }
    assert {r.establecimiento for r in comparar_producto(queso.pk)} == {
        "Minimercado Nuevo Centro"  # perecedero, 2 días
    }
