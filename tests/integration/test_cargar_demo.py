"""Punto 0: cargar_demo crea accesos sin contraseñas en el código y carga precios vencidos."""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.catalogo.domain.codigo_barras import es_gtin_valido
from apps.catalogo.models import Presentacion, Producto
from apps.catalogo.selectors import productos_por_codigo
from apps.comparacion.selectors import comparar_producto
from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento
from apps.precios import services
from apps.precios.models import ReportePrecio

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


def test_los_precios_de_ejemplo_no_agotan_el_cupo_de_registro(db, monkeypatch):
    # RN-10: 30 registros por hora. Los datos de ejemplo son históricos: no deben contar.
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", CLAVE)
    monkeypatch.setenv("DEMO_PASSWORD", CLAVE)
    _cargar("--con-vencidos")
    desde = timezone.now() - timedelta(hours=1)
    for usuario in Usuario.objects.filter(username__startswith="demo"):
        recientes = ReportePrecio.objects.filter(autor=usuario, creado_en__gte=desde).count()
        assert recientes == 0, (
            f"{usuario.username} ya tiene {recientes} registros en la última hora"
        )


def test_el_usuario_demo_puede_registrar_un_precio_justo_despues_de_cargar(db, monkeypatch):
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", CLAVE)
    monkeypatch.setenv("DEMO_PASSWORD", CLAVE)
    _cargar("--con-vencidos")
    reporte = services.registrar_reporte(  # no debe lanzar LimiteDeRegistrosExcedidoError
        autor=Usuario.objects.get(username="demo"),
        presentacion_id=Presentacion.objects.first().pk,
        establecimiento_id=Establecimiento.objects.filter(activo=True).first().pk,
        precio=Decimal("3333"),
    )
    assert reporte.pk is not None


def test_demo_incluye_codigos_de_barras_validos_para_ensayar_el_escaner(db):
    call_command("cargar_demo", stdout=StringIO())
    codigos = list(
        Presentacion.objects.exclude(codigo_barras="").values_list("codigo_barras", flat=True)
    )
    assert codigos and all(es_gtin_valido(c) for c in codigos)
    assert [p.nombre for p in productos_por_codigo(codigos[0])] == ["Arroz blanco"]
