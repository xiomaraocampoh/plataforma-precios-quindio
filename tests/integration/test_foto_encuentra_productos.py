"""Bug: la búsqueda por foto reconocía el producto pero decía que no estaba en el catálogo.

Causa: el nombre y la marca de la pista se unían en una sola frase («Arroz blanco Diana») y se
buscaba la frase completa; además la IA da nombres genéricos («Pasta spaghetti»). Ahora la vista
usa catalogo.buscar_por_pista, que puntúa marca, palabras del nombre y presentación.
"""

import re
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.administracion.services import datos_prueba
from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.catalogo.services import marca_por_nombre
from apps.integraciones import services
from apps.integraciones.domain.reconocimiento import PistaProducto

pytestmark = pytest.mark.integration

JPEG = b"\xff\xd8\xff\xe0" + b"1234"
_ENLACE = re.compile(r'href="/productos/(\d+)/"')


class Falso:
    def __init__(self):
        self.resultado = None

    def reconocer(self, imagen, tipo):
        return self.resultado


@pytest.fixture(autouse=True)
def _ajustes(settings):
    cache.clear()
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
        "RECONOCIMIENTOS_POR_HORA": 100,
        "RECONOCIMIENTOS_ANONIMO_POR_HORA": 100,
        "RECONOCIMIENTOS_POR_DIA_TOTAL": 100,
    }
    yield
    cache.clear()


@pytest.fixture
def catalogo(db):
    datos_prueba.cargar(solo_catalogo=True)
    cat, _ = Categoria.objects.get_or_create(nombre="Enlatados")
    for marca in ("Van Camp's", "Isabel"):
        p = Producto.objects.create(
            nombre="Atún en agua",
            nombre_normalizado="atun en agua",
            marca=marca_por_nombre(marca),
            categoria=cat,
        )
        Presentacion.objects.create(producto=p, cantidad=Decimal(160), unidad="g")


@pytest.fixture
def falso(monkeypatch):
    f = Falso()
    monkeypatch.setattr(services, "_crear_reconocedor", lambda: f)
    return f


def _candidatos(client, falso, nombre, marca="", cantidad="", unidad="") -> tuple[list, str]:
    from django.core.files.uploadedfile import SimpleUploadedFile

    falso.resultado = PistaProducto(nombre, marca, cantidad, unidad, "", "alta")
    r = client.post(
        reverse("comparacion:buscar_por_foto"), {"foto": SimpleUploadedFile("f.jpg", JPEG)}
    )
    assert r.status_code == 200
    html = r.content.decode()
    ids = list(dict.fromkeys(int(i) for i in _ENLACE.findall(html)))
    return [Producto.objects.select_related("marca").get(pk=i) for i in ids], html


def _marcas(productos) -> set[str]:
    return {p.marca.nombre for p in productos}


def test_arroz_diana_con_tamano_trae_el_premium_de_diana_primero(client, catalogo, falso):
    productos, html = _candidatos(client, falso, "Arroz blanco", "Diana", "500", "g")
    assert productos, "dijo que no lo tenemos"
    assert (productos[0].nombre, productos[0].marca.nombre) == ("Arroz blanco premium", "Diana")
    assert "Coincidencia más probable" in html


def test_nombre_generico_de_la_ia_encuentra_el_spaghetti_doria(client, catalogo, falso):
    productos, _ = _candidatos(client, falso, "Pasta spaghetti", "Doria")
    assert (productos[0].nombre, productos[0].marca.nombre) == ("Spaghetti", "Doria")


def test_cafe_sello_rojo(client, catalogo, falso):
    productos, _ = _candidatos(client, falso, "Café", "Sello Rojo")
    assert productos[0].marca.nombre == "Sello Rojo" and "Café" in productos[0].nombre


def test_sin_marca_trae_spaghetti_de_varias_marcas(client, catalogo, falso):
    productos, _ = _candidatos(client, falso, "Spaghetti")
    assert len(_marcas(productos)) >= 3
    assert all("spaghetti" in p.nombre_normalizado for p in productos)


def test_una_marca_inexistente_no_filtra_los_atunes(client, catalogo, falso):
    productos, _ = _candidatos(client, falso, "Atún", "Marca inexistente")
    assert _marcas(productos) == {"Van Camp's", "Isabel"}


def test_sin_nada_parecido_no_hay_candidatos_y_ofrece_buscar_por_texto(client, catalogo, falso):
    productos, html = _candidatos(client, falso, "Zapatos deportivos", "Nike")
    assert productos == []
    assert "Aún no está en nuestro catálogo" in html
    assert f"{reverse('comparacion:productos')}?q=Zapatos%20deportivos" in html
    assert "Buscar «Zapatos deportivos» por texto" in html


def test_no_redirige_sola_la_persona_confirma(client, catalogo, falso):
    falso.resultado = PistaProducto("Spaghetti", "Doria", "", "", "", "alta")
    from django.core.files.uploadedfile import SimpleUploadedFile

    r = client.post(
        reverse("comparacion:buscar_por_foto"), {"foto": SimpleUploadedFile("f.jpg", JPEG)}
    )
    assert r.status_code == 200 and "HX-Redirect" not in r.headers
