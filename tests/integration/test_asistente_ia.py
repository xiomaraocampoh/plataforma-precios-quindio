"""K-nasta con IA (ADR-0030), probada con un modelo falso: sin red ni gasto.

EC-14: la IA no inventa cifras. M-24: faltantes correctos. M-15: nada del reportante.
"""

import json
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.integraciones import services as integraciones
from apps.integraciones.clients.asistente import AsistenteNoDisponibleError, RespuestaModelo
from apps.precios import services

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpia():
    cache.clear()


@pytest.fixture
def ia_activa(settings):
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ASISTENTE_IA_ACTIVO": True,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
    }


class ModeloFalso:
    """Devuelve respuestas predefinidas, en orden, y guarda lo que recibió."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.recibido = []

    def responder(self, *, sistema, mensajes, herramientas):
        self.recibido.append({"sistema": sistema, "mensajes": json.loads(json.dumps(mensajes))})
        siguiente = self.respuestas.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


def _usa(nombre, **entrada):
    return {"type": "tool_use", "id": f"t-{nombre}", "name": nombre, "input": entrada}


def _herramientas(*llamadas):
    return RespuestaModelo(parada="tool_use", bloques=list(llamadas))


def _texto(texto):
    return RespuestaModelo(parada="end_turn", bloques=[{"type": "text", "text": texto}])


@pytest.fixture
def modelo(monkeypatch):
    def instalar(*respuestas):
        falso = ModeloFalso(*respuestas)
        monkeypatch.setattr(integraciones, "crear_asistente", lambda: falso)
        return falso

    return instalar


@pytest.fixture
def leche(db):
    cat = Categoria.objects.create(nombre="Lácteos")
    prod = Producto.objects.create(nombre="Leche", nombre_normalizado="leche", categoria=cat)
    return prod, Presentacion.objects.create(producto=prod, cantidad=Decimal("1"), unidad="L")


@pytest.fixture
def mercado(reportante, arroz, leche, tiendas):
    _, _, p1kg = arroz
    rosa, super_ = tiendas
    for pres, tienda, precio in [
        (p1kg, rosa, 5000),
        (p1kg, super_, 7000),
        (leche[1], super_, 4000),
    ]:
        services.registrar_reporte(
            autor=reportante, presentacion_id=pres.pk, establecimiento_id=tienda.pk, precio=precio
        )
    return arroz[0], leche[0]


def _decir(client, texto="", archivo=None):
    datos = {"mensaje": texto}
    if archivo is not None:
        datos["archivo"] = archivo
    return client.post(reverse("canasta:enviar"), datos).content.decode()


def _flujo_completo(arroz, leche, texto_final):
    """La IA busca, arma la lista, calcula y explica."""
    return [
        _herramientas(_usa("buscar_productos", textos=["arroz", "leche"])),
        _herramientas(
            _usa(
                "armar_canasta",
                items=[
                    {"producto_id": arroz.pk, "cantidad": 2, "unidad": "kg"},
                    {"producto_id": leche.pk, "cantidad": 1, "unidad": "L"},
                ],
            )
        ),
        _herramientas(_usa("calcular_canasta", criterio="cobertura")),
        _texto(texto_final),
    ]


def test_la_ia_arma_la_lista_calcula_y_explica_con_cifras_del_sistema(
    client, ia_activa, modelo, mercado
):
    arroz, leche = mercado
    falso = modelo(*_flujo_completo(arroz, leche, "Te conviene Súper Quindío: sale en $18.000."))
    html = _decir(client, "mercado de la semana: arroz y leche")
    assert "Te conviene Súper Quindío: sale en $18.000." in html
    assert (
        'class="cc-res es-mejor"' in html and "Tiene todo (2 de 2)" in html
    )  # tarjeta del sistema
    assert len(falso.recibido) == 4


def test_una_cifra_inventada_por_la_ia_se_descarta_y_el_sistema_redacta(
    client, ia_activa, modelo, mercado
):
    arroz, leche = mercado
    modelo(*_flujo_completo(arroz, leche, "Te sale en $9.999, ¡una ganga!"))
    html = _decir(client, "arroz y leche")
    assert "9.999" not in html  # EC-14
    assert "Te conviene Súper Quindío" in html and "$18.000" in html


def test_la_ia_puede_hacer_una_pregunta_sin_armar_nada(client, ia_activa, modelo, mercado):
    modelo(_texto("¿Para cuántas personas es el mercado?"))
    html = _decir(client, "mercado de la semana")
    assert "¿Para cuántas personas es el mercado?" in html and "cc-res" not in html


def test_sin_resultados_un_monto_de_la_ia_se_descarta(client, ia_activa, modelo, mercado):
    modelo(_texto("El arroz vale $4.500 en todas partes."))
    html = _decir(client, "cuánto vale el arroz")
    assert "4.500" not in html and "No logré darte una respuesta confiable" in html


def test_un_error_de_la_herramienta_se_devuelve_como_dato_y_la_ia_corrige(
    client, ia_activa, modelo, mercado
):
    arroz, leche = mercado
    modelo(
        _herramientas(
            _usa("armar_canasta", items=[{"producto_id": arroz.pk, "cantidad": 2, "unidad": "L"}])
        ),
        _herramientas(
            _usa("armar_canasta", items=[{"producto_id": arroz.pk, "cantidad": 2, "unidad": "kg"}])
        ),
        _herramientas(_usa("calcular_canasta", criterio="cobertura")),
        _texto("Listo, te conviene Súper Quindío."),
    )
    falso_html = _decir(client, "2 litros de arroz")
    assert "Te conviene" in falso_html or "Súper Quindío" in falso_html


def test_el_bucle_se_corta_tras_seis_vueltas_y_el_sistema_responde(
    client, ia_activa, modelo, mercado
):
    arroz, leche = mercado
    buscar = _herramientas(_usa("buscar_productos", textos=["arroz", "leche"]))
    modelo(
        _herramientas(
            _usa("armar_canasta", items=[{"producto_id": arroz.pk, "cantidad": 1, "unidad": "kg"}])
        ),
        *[buscar] * 7,
    )
    html = _decir(client, "arroz")
    assert "Te conviene" in html  # el sistema redactó con lo calculado antes del corte


def test_si_la_ia_falla_sigue_el_modo_basico_y_lo_avisa(client, ia_activa, modelo, mercado):
    modelo(AsistenteNoDisponibleError("timeout"))
    html = _decir(client, "2 kg arroz, 1 L leche")
    assert "respondo en modo básico" in html and "Te conviene Súper Quindío" in html


def test_al_superar_el_tope_por_hora_sigue_el_modo_basico(
    client, ia_activa, modelo, mercado, settings
):
    settings.INTEGRACIONES = {**settings.INTEGRACIONES, "ASISTENTE_ANONIMO_POR_HORA": 1}
    modelo(_texto("Hola, ¿qué llevas?"))
    _decir(client, "hola")
    html = _decir(client, "2 kg arroz")
    assert "límite de consultas con IA" in html and "Te conviene" in html


def test_ordenes_cortas_no_gastan_ia(client, ia_activa, modelo, mercado):
    falso = modelo()  # si se llamara, fallaría: no hay respuestas
    _decir(client, "empezar de nuevo")
    assert falso.recibido == []


def test_el_modelo_recibe_la_lista_actual_y_el_historial(client, ia_activa, modelo, mercado):
    arroz, leche = mercado
    falso = modelo(*_flujo_completo(arroz, leche, "Te conviene Súper Quindío."), _texto("Claro."))
    _decir(client, "arroz y leche")
    _decir(client, "gracias")
    segunda = falso.recibido[-1]
    assert "LISTA ACTUAL" in segunda["sistema"] and "Arroz blanco" in segunda["sistema"]
    assert segunda["mensajes"][0]["role"] == "user" and len(segunda["mensajes"]) >= 3


def test_una_foto_de_la_lista_viaja_al_modelo_y_no_se_guarda(client, ia_activa, modelo, mercado):
    falso = modelo(_texto("Veo tu lista, ¿la armamos?"))
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 50
    html = _decir(client, "", SimpleUploadedFile("lista.png", png, "image/png"))
    bloques = falso.recibido[0]["mensajes"][-1]["content"]
    assert bloques[0]["type"] == "image" and bloques[0]["source"]["media_type"] == "image/png"
    assert "📎 lista.png" in html and "base64" not in html


def test_una_imagen_invalida_se_rechaza_sin_llegar_a_la_ia(client, ia_activa, modelo, mercado):
    falso = modelo()
    html = _decir(client, "", SimpleUploadedFile("x.png", b"no es una imagen", "image/png"))
    assert "Solo se aceptan fotos" in html and falso.recibido == []


def test_lo_que_ve_la_ia_no_expone_al_reportante(client, ia_activa, modelo, mercado, reportante):
    arroz, leche = mercado
    falso = modelo(*_flujo_completo(arroz, leche, "Te conviene Súper Quindío."))
    _decir(client, "arroz y leche")
    visto = json.dumps(falso.recibido, ensure_ascii=False)
    assert reportante.username not in visto  # M-15


def test_sin_ia_activa_todo_sigue_con_reglas(client, mercado):
    html = _decir(client, "2 kg arroz, 1 L leche")
    assert "Te conviene Súper Quindío" in html


def test_la_ia_puede_pedir_varias_busquedas_a_la_vez_sin_cortarse(
    client, ia_activa, modelo, mercado
):
    arroz, leche = mercado
    muchas = [_usa("buscar_productos", textos=["arroz"]) for _ in range(8)]  # 8 llamadas, 1 vuelta
    modelo(
        _herramientas(*muchas),
        _herramientas(
            _usa("armar_canasta", items=[{"producto_id": arroz.pk, "cantidad": 1, "unidad": "kg"}])
        ),
        _herramientas(_usa("calcular_canasta", criterio="cobertura")),
        _texto("Te conviene Súper Quindío."),
    )
    assert "Te conviene Súper Quindío." in _decir(client, "arroz")


def test_el_texto_del_chat_permite_negrita_pero_escapa_todo_el_html(client, ia_activa, modelo):
    modelo(_texto("Mira **Súper Quindío** <script>alert(1)</script> <b>x</b>"))
    html = _decir(client, "hola")
    assert "<strong>Súper Quindío</strong>" in html
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html
    assert "<b>x</b>" not in html
