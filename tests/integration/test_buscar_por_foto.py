"""Búsqueda de un producto por foto con IA (ADR-019): servicio, límites, privacidad y vista."""

from decimal import Decimal

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.integraciones import services
from apps.integraciones.clients.vision import ReconocimientoNoDisponibleError
from apps.integraciones.domain.reconocimiento import ImagenInvalidaError, PistaProducto

pytestmark = pytest.mark.integration

JPEG = b"\xff\xd8\xff\xe0" + b"1234"
PISTA = PistaProducto("Café molido", "", "250", "g", "", "alta")


class Falso:
    def __init__(self, resultado=PISTA, error=None):
        self.resultado, self.error, self.llamadas = resultado, error, 0

    def reconocer(self, imagen, tipo):
        self.llamadas += 1
        if self.error:
            raise self.error
        return self.resultado


@pytest.fixture(autouse=True)
def _limpio(settings):
    cache.clear()
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
        "RECONOCIMIENTOS_POR_HORA": 2,
    }
    yield
    cache.clear()


@pytest.fixture
def usuario(django_user_model):
    return django_user_model.objects.create_user(
        username="u1", password="clave-segura-123", acepto_tratamiento_datos=True
    )


@pytest.fixture
def cafe(db):
    cat = Categoria.objects.create(nombre="Abarrotes")
    p = Producto.objects.create(
        nombre="Café molido", nombre_normalizado="cafe molido", categoria=cat
    )
    Presentacion.objects.create(producto=p, cantidad=Decimal(250), unidad="g")
    return p


@pytest.fixture
def falso(monkeypatch):
    f = Falso()
    monkeypatch.setattr(services, "_crear_reconocedor", lambda: f)
    return f


def _subir(client, contenido=JPEG, nombre="foto.jpg"):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return client.post(
        reverse("comparacion:buscar_por_foto"), {"foto": SimpleUploadedFile(nombre, contenido)}
    )


# --- servicio ---------------------------------------------------------------------------------
def test_servicio_devuelve_la_pista(usuario, falso):
    assert services.reconocer_producto(usuario=usuario, imagen=JPEG) == PISTA


def test_servicio_rechaza_archivos_que_no_son_imagen_sin_llamar_a_la_ia(usuario, falso):
    with pytest.raises(ImagenInvalidaError):
        services.reconocer_producto(usuario=usuario, imagen=b"%PDF-1.7")
    assert falso.llamadas == 0


def test_servicio_limita_los_reconocimientos_por_hora(usuario, falso):
    services.reconocer_producto(usuario=usuario, imagen=JPEG)
    services.reconocer_producto(usuario=usuario, imagen=JPEG)
    with pytest.raises(services.LimiteDeReconocimientosExcedidoError):
        services.reconocer_producto(usuario=usuario, imagen=JPEG)
    assert falso.llamadas == 2


def test_el_limite_es_por_usuario(usuario, falso, django_user_model):
    otro = django_user_model.objects.create_user(username="u2", password="clave-segura-123")
    for _ in range(2):
        services.reconocer_producto(usuario=usuario, imagen=JPEG)
    assert services.reconocer_producto(usuario=otro, imagen=JPEG) == PISTA


# --- vista ------------------------------------------------------------------------------------
def test_exige_sesion(client, falso):
    r = _subir(client)
    assert r.status_code == 302 and "ingresar" in r.url
    assert falso.llamadas == 0


def test_solo_acepta_post(client, usuario):
    client.force_login(usuario)
    assert client.get(reverse("comparacion:buscar_por_foto")).status_code == 405


def test_reconocido_muestra_candidatos_para_confirmar(client, usuario, cafe, falso):
    client.force_login(usuario)
    r = _subir(client)
    assert r.status_code == 200
    html = r.content.decode()
    assert reverse("comparacion:comparar", args=[cafe.pk]) in html
    assert "Café molido" in html


def test_reconocido_pero_fuera_del_catalogo_ofrece_solicitarlo(client, usuario, falso):
    client.force_login(usuario)
    html = _subir(client).content.decode()
    assert reverse("catalogo:solicitar") in html
    assert "nombre=Caf" in html


def test_no_reconocido(client, usuario, falso):
    falso.resultado = None
    client.force_login(usuario)
    r = _subir(client)
    assert r.status_code == 200 and "No pudimos reconocer" in r.content.decode()


def test_archivo_invalido(client, usuario, falso):
    client.force_login(usuario)
    r = _subir(client, contenido=b"%PDF-1.7", nombre="a.pdf")
    assert r.status_code == 400 and falso.llamadas == 0


def test_sin_archivo(client, usuario, falso):
    client.force_login(usuario)
    r = client.post(reverse("comparacion:buscar_por_foto"), {})
    assert r.status_code == 400 and falso.llamadas == 0


def test_servicio_externo_caido_no_rompe_la_busqueda(client, usuario, falso):
    falso.error = ReconocimientoNoDisponibleError("x")
    client.force_login(usuario)
    r = _subir(client)
    assert r.status_code == 503 and "nombre o con el código" in r.content.decode()


def test_limite_excedido_responde_429(client, usuario, falso):
    client.force_login(usuario)
    _subir(client)
    _subir(client)
    r = _subir(client)
    assert r.status_code == 429


def test_la_respuesta_no_incluye_datos_de_personas(client, usuario, cafe, falso):
    client.force_login(usuario)
    html = _subir(client).content.decode().lower()
    assert "u1" not in html and "@" not in html  # M-15


def test_inicio_muestra_la_foto_solo_si_esta_activada(client, settings):
    assert "data-foto" in client.get(reverse("comparacion:inicio")).content.decode()
    settings.INTEGRACIONES = {**settings.INTEGRACIONES, "ANTHROPIC_API_KEY": ""}
    assert "data-foto" not in client.get(reverse("comparacion:inicio")).content.decode()
