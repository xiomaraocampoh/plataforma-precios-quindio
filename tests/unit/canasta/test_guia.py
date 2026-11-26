"""La guía de uso de AhorraPues que K-nasta enseña a quien llega por primera vez. Python puro."""

import pytest

from apps.canasta.domain.guia import TEMAS, buscar_temas, tema_por_id

pytestmark = pytest.mark.unit


def _mejor(texto):
    temas = buscar_temas(texto)
    return temas[0].id if temas else None


@pytest.mark.parametrize(
    ("pregunta", "tema"),
    [
        ("¿Cómo registro un precio?", "registrar"),
        ("quiero reportar un precio que vi hoy", "registrar"),
        ("cómo subo el precio de la leche", "registrar"),
        ("¿Cómo creo una cuenta?", "cuenta"),
        ("necesito registrarme", "cuenta"),
        ("cómo me inscribo en la página", "cuenta"),
        ("¿Cómo comparo precios?", "comparar"),
        ("donde veo cuál tienda es más barata para el arroz", "comparar"),
        ("cómo confirmo un precio", "confirmar"),
        ("como denuncio un precio que está mal", "confirmar"),
        ("cómo escaneo el código de barras", "escanear"),
        ("puedo buscar con la cámara?", "escanear"),
        ("por qué ya no aparece el precio", "vigencia"),
        ("qué significa confianza media", "vigencia"),
        ("no encuentro un producto", "producto_faltante"),
        ("cómo pido que agreguen un producto", "producto_faltante"),
        ("mi tienda no está en el directorio", "tienda_faltante"),
        ("cómo sugiero un establecimiento", "tienda_faltante"),
        ("donde veo mis aportes", "mis_aportes"),
        ("cómo activo el modo oscuro", "apariencia"),
        ("tengo un comercio, cómo publico mis precios", "comercio"),
        ("mis datos son públicos?", "privacidad"),
        ("olvidé mi contraseña", "contrasena"),
        ("qué es AhorraPues", "que_es"),
        ("para qué sirve esta página", "que_es"),
    ],
)
def test_encuentra_el_tema_de_cada_pregunta(pregunta, tema):
    assert _mejor(pregunta) == tema


def test_sin_relacion_no_hay_tema():
    assert buscar_temas("hola buenas tardes") == []
    assert buscar_temas("2 kg arroz, 1 L leche") == []
    assert buscar_temas("") == []


def test_devuelve_como_mucho_los_temas_pedidos_ordenados_por_afinidad():
    temas = buscar_temas("cómo registro un precio y creo una cuenta", limite=2)
    assert len(temas) == 2 and {t.id for t in temas} == {"registrar", "cuenta"}


def test_no_distingue_tildes_ni_mayusculas():
    assert _mejor("COMO REGISTRO UN PRECIO") == "registrar"
    assert _mejor("como registro un precio") == "registrar"


def test_cada_tema_tiene_pasos_palabras_y_destinos_validos():
    ids = [t.id for t in TEMAS]
    assert len(ids) == len(set(ids)) and len(ids) >= 12
    for t in TEMAS:
        assert t.titulo and len(t.pasos) >= 1 and t.patrones
        assert all(paso.strip() for paso in t.pasos)
        for texto, ruta in t.acciones:
            assert texto and ":" in ruta  # «app:nombre», para resolverla con reverse


def test_tema_por_id():
    assert tema_por_id("registrar").titulo.startswith("¿Cómo registro un precio")
    assert tema_por_id("no-existe") is None
