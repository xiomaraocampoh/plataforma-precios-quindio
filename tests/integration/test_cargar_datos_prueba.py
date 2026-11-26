"""cargar_datos_prueba: conteos, idempotencia, reglas de negocio y orden por precio por unidad."""

import csv
import shutil
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.catalogo.models import Marca, Presentacion, Producto, SolicitudCatalogo
from apps.catalogo.selectors import productos_por_codigo, productos_similares
from apps.comparacion.selectors import comparar_producto
from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento
from apps.moderacion.models import Denuncia
from apps.precios import services as precios
from apps.precios.models import ConfirmacionPrecio, ReportePrecio

pytestmark = pytest.mark.integration

DATOS = Path(settings.BASE_DIR) / "data" / "demo"


def _filas(archivo: str) -> list[dict]:
    with (DATOS / archivo).open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _cargar(*args) -> str:
    salida = StringIO()
    call_command("cargar_datos_prueba", *args, stdout=salida)
    return salida.getvalue()


def _producto(marca: str, nombre: str) -> Producto:
    return Producto.objects.get(marca__nombre=marca, nombre=nombre)


def _nombres_en_comparacion(producto: Producto) -> set[str]:
    return {r.establecimiento for r in comparar_producto(producto.pk)}


@pytest.fixture
def cargado(db):
    return _cargar()


def test_conteos_coinciden_con_los_csv_y_se_imprimen(cargado):
    aprobados = [f for f in _filas("establecimientos.csv") if f["estado"] == "aprobado"]
    assert Marca.objects.count() == len(_filas("marcas.csv"))
    assert Producto.objects.count() == len(_filas("productos.csv"))
    assert Presentacion.objects.count() == len(_filas("presentaciones.csv"))
    assert Establecimiento.objects.filter(activo=True).count() == len(aprobados)
    assert ReportePrecio.objects.filter(es_demo=True).count() == len(_filas("precios.csv"))
    assert f"Precios: {len(_filas('precios.csv'))} " in cargado
    assert "Marcas:" in cargado and "Establecimientos:" in cargado


def test_contenido_minimo_categorias_marcas_y_establecimientos(cargado):
    productos = _filas("productos.csv")
    categorias = {f["categoria"] for f in productos}
    assert len(categorias) >= 12
    for categoria in categorias:
        assert len({f["marca"] for f in productos if f["categoria"] == categoria}) >= 5
    for presentacion in Presentacion.objects.all():
        locales = set(
            ReportePrecio.objects.filter(presentacion=presentacion).values_list(
                "establecimiento", flat=True
            )
        )
        assert 3 <= len(locales) <= 6, presentacion
    ficticias = [f for f in _filas("establecimientos.csv") if f["ficticia"] == "si"]
    assert len([f for f in ficticias if f["estado"] == "aprobado"]) == 4


def test_cada_precio_lleva_fuente_y_fecha_de_consulta():
    for fila in _filas("precios.csv"):
        assert fila["fuente"] == "aproximado" or fila["fuente"].startswith("https://")
        assert fila["fecha_consulta"]


def test_es_idempotente(cargado):
    antes = {
        "marcas": Marca.objects.count(),
        "productos": Producto.objects.count(),
        "presentaciones": Presentacion.objects.count(),
        "establecimientos": Establecimiento.objects.count(),
        "precios": ReportePrecio.objects.count(),
        "confirmaciones": ConfirmacionPrecio.objects.count(),
        "denuncias": Denuncia.objects.count(),
        "solicitudes": SolicitudCatalogo.objects.count(),
    }
    segunda = _cargar()
    despues = {
        "marcas": Marca.objects.count(),
        "productos": Producto.objects.count(),
        "presentaciones": Presentacion.objects.count(),
        "establecimientos": Establecimiento.objects.count(),
        "precios": ReportePrecio.objects.count(),
        "confirmaciones": ConfirmacionPrecio.objects.count(),
        "denuncias": Denuncia.objects.count(),
        "solicitudes": SolicitudCatalogo.objects.count(),
    }
    assert antes == despues
    assert "(0 nuevos)" in segunda and "Precios: 438 (0 nuevos)" in segunda


def test_la_comparacion_ordena_por_precio_por_unidad(cargado):  # M-06, EC-06
    roa = _producto("Roa", "Arroz blanco")  # 500 g y 1 kg del mismo producto
    resultados = comparar_producto(roa.pk)
    unitarios = [r.precio_unitario for r in resultados]
    assert unitarios == sorted(unitarios)
    assert {r.unidad_base for r in resultados} == {"kg"}
    assert {"Arroz blanco Roa 500 g", "Arroz blanco Roa 1 kg"} <= {
        r.presentacion for r in resultados
    }
    for r in resultados:  # el precio por unidad sale de la presentación, no del precio total
        cantidad_kg = Decimal("0.5") if "500 g" in r.presentacion else Decimal("1")
        assert r.precio_unitario == (r.precio / cantidad_kg).quantize(Decimal("0.01"))


def test_vencidos_no_se_muestran_y_los_del_limite_si(cargado):  # EC-02
    florhuila = _nombres_en_comparacion(_producto("Florhuila", "Arroz blanco"))
    assert "Tienda El Paisa" not in florhuila  # 8 días, reportado
    assert "Tienda La Bendición" in florhuila  # 6 días
    colanta = _nombres_en_comparacion(_producto("Colanta", "Leche entera"))
    assert "Tienda Doña Gloria" not in colanta  # 4 días, perecedero
    assert "Tienda El Paisa" in colanta  # 2 días
    corona = _nombres_en_comparacion(_producto("Corona", "Chocolate de mesa tradicional"))
    assert "Olímpica Portal del Quindío" not in corona  # 31 días, oficial
    assert "Éxito Calarcá" in corona  # 29 días, oficial


def test_el_precio_anomalo_queda_en_revision(cargado):  # EC-03
    cafe = _producto("Sello Rojo", "Café molido")
    anomalo = ReportePrecio.objects.get(
        presentacion__producto=cafe, establecimiento__nombre="D1 Granada", precio=Decimal("31500")
    )
    assert anomalo.estado == ReportePrecio.Estado.EN_REVISION
    en_d1 = [r for r in comparar_producto(cafe.pk) if r.establecimiento == "D1 Granada"]
    assert [r.precio for r in en_d1] == [Decimal("19700")]  # se sigue viendo el último publicado


def test_varios_reportes_iguales_dan_confianza_alta(cargado):
    diana = _producto("Diana", "Arroz blanco premium")
    ara = [r for r in comparar_producto(diana.pk) if r.establecimiento == "Ara Centro Armenia"]
    assert [r.confianza for r in ara] == ["alta"]


def test_escenarios_de_moderacion_y_escaner(cargado):
    assert ConfirmacionPrecio.objects.count() == 4
    assert Denuncia.objects.filter(estado=Denuncia.Estado.ABIERTA).count() == 2
    solicitud = SolicitudCatalogo.objects.get(nombre="Arroz blanco premiun")
    assert solicitud.estado == SolicitudCatalogo.Estado.PENDIENTE
    assert productos_similares(solicitud.nombre, solicitud.marca)  # D-05: hay un parecido
    sugerido = Establecimiento.objects.get(nombre="Tienda La Esperanza")
    assert sugerido.estado == Establecimiento.Estado.PENDIENTE and not sugerido.activo
    assert [str(p) for p in productos_por_codigo("7702511000021")] == ["Arroz blanco premium Diana"]


def test_los_autores_sin_contrasena_utilizable(cargado):
    autores = Usuario.objects.filter(reportes__es_demo=True).distinct()
    assert autores.exists()
    assert all(u.es_cuenta_prueba and not u.has_usable_password() for u in autores)


def test_solo_catalogo_no_carga_precios(db):
    _cargar("--solo-catalogo")
    assert Producto.objects.count() == len(_filas("productos.csv"))
    assert not ReportePrecio.objects.exists()
    assert not Usuario.objects.filter(es_cuenta_prueba=True).exists()


def test_limpiar_borra_lo_de_prueba_y_conserva_lo_real(cargado):
    diana = Presentacion.objects.get(producto__marca__nombre="Diana", cantidad=1, unidad="kg")
    real = precios.cargar_reporte_historico(
        autor=Usuario.objects.create_user(username="persona_real", password=None),
        presentacion_id=diana.pk,
        establecimiento_id=Establecimiento.objects.get(nombre="D1 Granada").pk,
        precio=Decimal("6100"),
        fecha_observacion=timezone.now(),
    )
    salida = _cargar("--limpiar", "--solo-catalogo")
    assert "Datos de prueba borrados" in salida
    assert list(ReportePrecio.objects.all()) == [real]
    assert not Denuncia.objects.exists() and not ConfirmacionPrecio.objects.exists()
    assert not SolicitudCatalogo.objects.exists()
    assert not Establecimiento.objects.filter(nombre="Tienda La Esperanza").exists()
    # --solo-catalogo vuelve a crear el catálogo: está completo y sin duplicados
    assert Producto.objects.count() == len(_filas("productos.csv"))


def test_una_fila_invalida_no_deja_nada_a_medias(db, tmp_path):
    destino = tmp_path / "demo"
    shutil.copytree(DATOS, destino)
    ruta = destino / "precios.csv"
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    lineas[5] = lineas[5].replace(",reportante,", ",inventada,", 1)
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    with pytest.raises(CommandError, match="precios.csv línea 6"):
        _cargar("--directorio", str(destino))
    assert not Producto.objects.exists() and not ReportePrecio.objects.exists()


@pytest.mark.django_db
def test_los_datos_de_prueba_quedan_en_sus_departamentos():
    from django.core.management import call_command

    from apps.catalogo.models import Categoria

    call_command("cargar_datos_prueba", "--solo-catalogo")
    esperado = {
        "Arroz": "mercado",
        "Leche": "lacteos_huevos",
        "Detergente": "aseo_hogar",
        "Crema dental": "salud_belleza",
    }
    for nombre, grupo in esperado.items():
        assert Categoria.objects.get(nombre=nombre).grupo == grupo
