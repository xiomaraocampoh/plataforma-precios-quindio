"""Siembra en migraciones (ADR-0023): `migrate` deja los datos de data/demo/ y las cuentas base.

La base de pruebas nace sin semilla (config/settings/test.py y DEBUG=False). Aquí la siembra se
activa con override_settings: con las migraciones reales (adelante y en reversa) o llamando a sus
funciones con el registro de modelos.
"""

import importlib
import secrets
from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.apps import apps as registro
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.administracion.services import datos_prueba
from apps.catalogo.models import Categoria, Marca, Presentacion, Producto, SolicitudCatalogo
from apps.comparacion.selectors import comparar_producto
from apps.cuentas.domain.cuentas_prueba import CUENTAS_PRUEBA, VARIABLE_CONTRASENA
from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento
from apps.moderacion.models import Denuncia
from apps.precios import services as precios
from apps.precios.models import ConfirmacionPrecio, ReportePrecio
from apps.precios.semilla import id_cliente

pytestmark = pytest.mark.integration

# Conteos del resumen del PR #17 (data/demo/README.md)
ESPERADO = {
    "marcas": 67,
    "categorias": 14,
    "productos": 70,
    "presentaciones": 97,
    "establecimientos": 12,  # aprobados; además 1 sugerido pendiente
    "precios": 438,
    "en_revision": 1,
    "sigue_igual": 4,
    "denuncias": 2,
    "solicitudes": 2,
    "sugeridos": 1,
    "cuentas": len(CUENTAS_PRUEBA),
}

ANTES_DE_LA_SEMILLA = [
    ("catalogo", "0007_activos"),
    ("establecimientos", "0003_tipos_discount_y_plaza"),
    ("cuentas", "0005_usuario_es_cuenta_prueba"),  # arrastra a precios.0004 (depende de ella)
]

MIGRACIONES = {
    "catalogo": "apps.catalogo.migrations.0008_semilla_catalogo",
    "establecimientos": "apps.establecimientos.migrations.0004_semilla_directorio",
    "cuentas": "apps.cuentas.migrations.0006_semilla_cuentas_prueba",
    "precios": "apps.precios.migrations.0004_semilla_precios_prueba",
}


def _conteos() -> dict[str, int]:
    return {
        "marcas": Marca.objects.count(),
        "categorias": Categoria.objects.count(),
        "productos": Producto.objects.count(),
        "presentaciones": Presentacion.objects.count(),
        "establecimientos": Establecimiento.objects.filter(estado="aprobado").count(),
        "precios": ReportePrecio.objects.filter(es_demo=True).count(),
        "en_revision": ReportePrecio.objects.filter(estado="en_revision").count(),
        "sigue_igual": ConfirmacionPrecio.objects.count(),
        "denuncias": Denuncia.objects.filter(estado="abierta").count(),
        "solicitudes": SolicitudCatalogo.objects.filter(estado="pendiente").count(),
        "sugeridos": Establecimiento.objects.filter(estado="pendiente").count(),
        "cuentas": Usuario.objects.filter(es_cuenta_prueba=True).count(),
    }


def _vacia() -> dict[str, int]:
    return dict.fromkeys(ESPERADO, 0)


def _migrar(*destino) -> None:
    call_command("migrate", *destino, verbosity=0, stdout=StringIO())


def _sembrar_como_migrate() -> None:
    """Las cuatro funciones de las migraciones, en su orden, con el registro de modelos."""
    for app in ("catalogo", "establecimientos", "cuentas", "precios"):
        importlib.import_module(MIGRACIONES[app]).sembrar(registro, None)


def _producto(marca: str, nombre: str) -> Producto:
    return Producto.objects.get(marca__nombre=marca, nombre=nombre)


def _locales_en_comparacion(producto: Producto) -> set[str]:
    return {r.establecimiento for r in comparar_producto(producto.pk)}


@pytest.fixture
def sin_clave(monkeypatch):
    monkeypatch.delenv(VARIABLE_CONTRASENA, raising=False)


@pytest.fixture
def clave(monkeypatch):
    valor = secrets.token_urlsafe(16)  # nunca un literal en el código
    monkeypatch.setenv(VARIABLE_CONTRASENA, valor)
    return valor


# ---------- las migraciones reales ----------


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_migrate_en_base_vacia_siembra_y_la_reversa_la_deja_como_estaba(sin_clave):
    _migrar("catalogo", "0007_activos")  # sin datos que revertir: la base sigue vacía
    for app, nombre in ANTES_DE_LA_SEMILLA[1:]:
        _migrar(app, nombre)
    assert _conteos() == _vacia()
    try:
        _migrar()  # base vacía + migrate
        assert _conteos() == ESPERADO
        for app, nombre in ANTES_DE_LA_SEMILLA:
            _migrar(app, nombre)
        assert _conteos() == _vacia()  # la reversa quita solo lo sembrado
    finally:
        _migrar()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_migrate_despues_de_cargar_datos_prueba_no_duplica(sin_clave):
    for app, nombre in ANTES_DE_LA_SEMILLA:
        _migrar(app, nombre)
    try:
        call_command("cargar_datos_prueba", stdout=StringIO())
        cargado = _conteos()
        _migrar()
        assert _conteos() == cargado == ESPERADO
    finally:
        _migrar()


@pytest.mark.django_db(transaction=True)
@override_settings(DEBUG=True)
def test_la_reversa_conserva_lo_que_usan_los_datos_reales(sin_clave):
    _sembrar_como_migrate()
    diana = Presentacion.objects.get(producto__marca__nombre="Diana", cantidad=1, unidad="kg")
    real = precios.cargar_reporte_historico(
        autor=Usuario.objects.create_user(username="persona_real", password=None),
        presentacion_id=diana.pk,
        establecimiento_id=Establecimiento.objects.get(nombre="D1 Granada").pk,
        precio=Decimal("6100"),
        fecha_observacion=timezone.now(),
    )
    try:
        for app, nombre in ANTES_DE_LA_SEMILLA:
            _migrar(app, nombre)
        assert list(ReportePrecio.objects.all()) == [real]
        assert Presentacion.objects.filter(pk=diana.pk).exists()
        assert Establecimiento.objects.filter(nombre="D1 Granada").exists()
        assert Producto.objects.count() == 1 and Marca.objects.count() == 1
    finally:
        _migrar()


# ---------- idempotencia ----------


@override_settings(DEBUG=True)
def test_sembrar_dos_veces_no_duplica(db, sin_clave):
    _sembrar_como_migrate()
    _sembrar_como_migrate()
    assert _conteos() == ESPERADO


@override_settings(DEBUG=True)
def test_cargar_datos_prueba_despues_de_la_semilla_no_duplica(db, sin_clave):
    _sembrar_como_migrate()
    salida = StringIO()
    call_command("cargar_datos_prueba", stdout=salida)
    assert _conteos() == ESPERADO
    assert "Precios: 438 (0 nuevos)" in salida.getvalue()


# ---------- reglas de negocio de lo sembrado ----------


@override_settings(DEBUG=True)
def test_la_comparacion_muestra_vigentes_y_oculta_vencidos(db, sin_clave):  # EC-02
    _sembrar_como_migrate()
    florhuila = _locales_en_comparacion(_producto("Florhuila", "Arroz blanco"))
    assert "Tienda La Bendición" in florhuila  # 6 días: vigente
    assert "Tienda El Paisa" not in florhuila  # 8 días: vencido
    colanta = _locales_en_comparacion(_producto("Colanta", "Leche entera"))
    assert "Tienda El Paisa" in colanta and "Tienda Doña Gloria" not in colanta  # perecedero
    corona = _locales_en_comparacion(_producto("Corona", "Chocolate de mesa tradicional"))
    assert "Éxito Calarcá" in corona and "Olímpica Portal del Quindío" not in corona  # oficial


@override_settings(DEBUG=True)
def test_el_anomalo_en_revision_y_la_confianza_alta(db, sin_clave):  # EC-03
    _sembrar_como_migrate()
    cafe = _producto("Sello Rojo", "Café molido")
    anomalo = ReportePrecio.objects.get(presentacion__producto=cafe, precio=Decimal("31500"))
    assert anomalo.estado == ReportePrecio.Estado.EN_REVISION
    diana = _producto("Diana", "Arroz blanco premium")
    ara = [r for r in comparar_producto(diana.pk) if r.establecimiento == "Ara Centro Armenia"]
    assert [r.confianza for r in ara] == ["alta"]  # 3 reportes iguales


# ---------- cuentas y contraseña ----------


@override_settings(DEBUG=True)
def test_con_la_variable_las_cuentas_inician_sesion(client, db, clave):
    _sembrar_como_migrate()
    for cuenta in CUENTAS_PRUEBA:
        usuario = Usuario.objects.get(username=cuenta.usuario)
        assert usuario.check_password(clave)
        assert usuario.email == cuenta.correo and usuario.email_verificado_en is not None
        assert usuario.acepto_tratamiento_datos and usuario.is_active is cuenta.activa
    assert Usuario.objects.get(username="reportante_prueba").groups.filter(name="Reportante")
    client.post(reverse("cuentas:ingresar"), {"username": "reportante_prueba", "password": clave})
    assert "_auth_user_id" in client.session


@override_settings(DEBUG=True)
def test_sin_la_variable_quedan_con_contrasena_inutilizable_y_avisa(db, sin_clave, capsys):
    importlib.import_module(MIGRACIONES["cuentas"]).sembrar(registro, None)
    assert Usuario.objects.filter(es_cuenta_prueba=True).count() == len(CUENTAS_PRUEBA)
    assert not any(u.has_usable_password() for u in Usuario.objects.filter(es_cuenta_prueba=True))
    salida = capsys.readouterr().out
    assert (
        "Define CUENTAS_PRUEBA_PASSWORD y corre python manage.py crear_cuentas_prueba "
        "para activarlas" in salida
    )


@override_settings(DEBUG=True)
def test_una_contrasena_debil_no_se_usa_ni_se_muestra(db, monkeypatch, capsys):
    monkeypatch.setenv(VARIABLE_CONTRASENA, "1234")
    importlib.import_module(MIGRACIONES["cuentas"]).sembrar(registro, None)
    assert not any(u.has_usable_password() for u in Usuario.objects.filter(es_cuenta_prueba=True))
    assert "1234" not in capsys.readouterr().out


@override_settings(DEBUG=True)
def test_migrate_no_cambia_la_contrasena_de_una_cuenta_existente(db, clave, monkeypatch):
    call_command("crear_cuentas_prueba", stdout=StringIO())
    monkeypatch.setenv(VARIABLE_CONTRASENA, secrets.token_urlsafe(16))  # otra clave en el .env
    importlib.import_module(MIGRACIONES["cuentas"]).sembrar(registro, None)
    assert Usuario.objects.get(username="admin_prueba").check_password(clave)


@override_settings(DEBUG=True, CUENTAS_PRUEBA_CORREO_BASE="equipo@correo.test")
def test_la_semilla_usa_el_correo_base(db, sin_clave):
    importlib.import_module(MIGRACIONES["cuentas"]).sembrar(registro, None)
    correos = dict(Usuario.objects.values_list("username", "email"))
    assert correos == {c.usuario: f"equipo+{c.sufijo}@correo.test" for c in CUENTAS_PRUEBA}


# ---------- producción ----------


@override_settings(DEBUG=False, SEMBRAR_CUENTAS_PRUEBA=False, SEMBRAR_DATOS_PRUEBA=False)
def test_en_produccion_sin_las_variables_no_siembra_nada(db, clave):
    _sembrar_como_migrate()
    assert _conteos() == _vacia()
    assert not Usuario.objects.exists()


@override_settings(DEBUG=False, SEMBRAR_CUENTAS_PRUEBA=True)
def test_en_produccion_con_sembrar_cuentas_si_las_crea(db, clave):
    importlib.import_module(MIGRACIONES["cuentas"]).sembrar(registro, None)
    assert Usuario.objects.filter(es_cuenta_prueba=True).count() == len(CUENTAS_PRUEBA)


@override_settings(DEBUG=False, SEMBRAR_DATOS_PRUEBA=True, SEMBRAR_CUENTAS_PRUEBA=False)
def test_datos_sin_cuentas_siembra_el_catalogo_pero_no_los_precios(db, clave, capsys):
    _sembrar_como_migrate()
    assert Producto.objects.count() == ESPERADO["productos"]
    assert not ReportePrecio.objects.exists() and not Usuario.objects.exists()
    assert "faltan las cuentas de prueba" in capsys.readouterr().out


# ---------- refrescar_precios_prueba ----------


def test_refrescar_renueva_las_fechas_sin_mover_los_reales(
    db, sin_clave, django_capture_on_commit_callbacks
):
    hace_20_dias = timezone.now() - timedelta(days=20)
    datos_prueba.cargar(ahora=hace_20_dias)  # todo quedó viejo
    florhuila = _producto("Florhuila", "Arroz blanco")
    assert "Tienda La Bendición" not in _locales_en_comparacion(florhuila)
    real = precios.cargar_reporte_historico(
        autor=Usuario.objects.create_user(username="persona_real", password=None),
        presentacion_id=Presentacion.objects.filter(producto=florhuila).first().pk,
        establecimiento_id=Establecimiento.objects.get(nombre="D1 Granada").pk,
        precio=Decimal("4000"),
        fecha_observacion=hace_20_dias,
    )
    salida = StringIO()
    with django_capture_on_commit_callbacks(execute=True):  # invalida la caché (ADR-0002)
        call_command("refrescar_precios_prueba", stdout=salida)
    assert "438 precios de prueba" in salida.getvalue()
    locales = _locales_en_comparacion(florhuila)
    assert "Tienda La Bendición" in locales  # vuelve a estar a 6 días
    assert "Tienda El Paisa" not in locales  # el vencido sigue vencido (8 días)
    real.refresh_from_db()
    assert real.fecha_observacion == hace_20_dias
    primero = ReportePrecio.objects.get(id_cliente=id_cliente("P0001"))
    assert timezone.now() - primero.fecha_observacion < timedelta(minutes=1)  # «hace 0 días»
    assert ConfirmacionPrecio.objects.filter(fecha=timezone.localdate()).count() == 4
