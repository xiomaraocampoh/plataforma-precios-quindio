"""Semilla del módulo comercial (ADR-0023): dos comercios verificados con precios oficiales y una
promoción de cada tipo. Idempotente, sin tocar datos existentes y reversible."""

import pytest
from django.apps import apps as registro
from django.utils import timezone

from apps.administracion.services import datos_prueba
from apps.catalogo.models import Producto
from apps.comercios import semilla
from apps.comercios.models import PerfilComercio, PrecioOficial, Promocion
from apps.comparacion.selectors import comparar_filas
from apps.cuentas.models import Usuario
from apps.precios.models import ReportePrecio

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def datos(db):
    datos_prueba.cargar()  # catálogo, directorio, precios y cuentas de prueba (sin contraseña)


def test_siembra_dos_comercios_verificados_y_una_promocion_de_cada_tipo(datos):
    reportes_antes = ReportePrecio.objects.count()
    nuevos, avisos = semilla.sembrar(registro, ahora=timezone.now())
    assert (nuevos, avisos) == (2, [])
    perfiles = PerfilComercio.objects.select_related("usuario", "verificado_por")
    assert {p.establecimiento.nombre for p in perfiles} == {"Tienda Doña Gloria", "Tienda El Paisa"}
    assert all(p.verificado and p.verificado_por.username == "moderador_prueba" for p in perfiles)
    assert set(Promocion.objects.values_list("tipo", flat=True)) == {
        "descuento_porcentual",
        "precio_especial",
        "pague_x_lleve_y",
    }
    assert PrecioOficial.objects.count() == 5
    assert ReportePrecio.objects.count() == reportes_antes  # no cambia datos existentes
    assert Usuario.objects.get(username="comercio_prueba").rol == "comercio"


def test_la_siembra_es_idempotente_y_reversible(datos):
    semilla.sembrar(registro, ahora=timezone.now())
    assert semilla.sembrar(registro, ahora=timezone.now()) == (0, [])
    semilla.revertir(registro)
    assert not PerfilComercio.objects.exists() and not PrecioOficial.objects.exists()
    assert not Usuario.objects.filter(username=semilla.DUENA_NUEVA).exists()
    assert Usuario.objects.filter(username="comercio_prueba").exists()  # la cuenta base queda


def test_los_precios_sembrados_salen_como_oficiales_en_la_comparacion(datos):
    semilla.sembrar(registro, ahora=timezone.now())
    arroz = Producto.objects.get(nombre="Arroz blanco", marca__nombre="Supremo")
    oficiales = [f for f in comparar_filas(arroz.pk) if f.es_oficial]
    assert {f.resultado.establecimiento for f in oficiales} == {
        "Tienda Doña Gloria",
        "Tienda El Paisa",
    }
    assert any(f.resultado.es_promocion for f in oficiales)


def test_sin_moderador_de_prueba_no_siembra(db):
    nuevos, avisos = semilla.sembrar(registro, ahora=timezone.now())
    assert nuevos == 0 and "moderador_prueba" in avisos[0]
