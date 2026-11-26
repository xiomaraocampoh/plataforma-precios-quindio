"""K-nasta enseña a usar la app a quien llega por primera vez (con y sin IA).

Todo lo que dice sale de la guía (apps/canasta/domain/guia.py): nada se inventa.
"""

import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from apps.canasta.domain.guia import TEMAS, buscar_temas, tema_por_id
from apps.integraciones import services as integraciones
from apps.integraciones.clients.asistente import RespuestaModelo

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _cache_limpia():
    cache.clear()


def _decir(client, texto, **extra):
    return client.post(reverse("canasta:enviar"), {"mensaje": texto, **extra}).content.decode()


# --- sin IA: K-nasta responde con la guía -------------------------------------------------------
def test_la_guia_responde_una_pregunta_con_pasos_y_botones_que_funcionan(client):
    html = _decir(client, "¿Cómo registro un precio?")
    assert "<strong>¿Cómo registro un precio?</strong>" in html
    assert "Guardar precio" in html and "Registrar precio aquí" in html
    assert 'href="/precios/registrar/"' in html  # botón de acceso directo
    assert 'href="/cuentas/registro/"' in html


def test_cada_destino_de_la_guia_es_una_ruta_que_existe(client):
    for tema in TEMAS:
        for texto, ruta in tema.acciones:
            assert reverse(ruta).startswith("/"), (tema.id, texto)


def test_cada_titulo_de_la_guia_lleva_a_su_propio_tema():
    for tema in TEMAS:
        assert buscar_temas(tema.titulo)[0].id == tema.id, tema.titulo


def test_una_pregunta_sin_tema_ofrece_los_temas_principales(client):
    html = _decir(client, "¿Cómo hago para teletransportarme?")
    assert "Con gusto te ayudo a usar AhorraPues" in html
    assert 'name="tema" value="registrar"' in html


def test_un_tema_relacionado_se_ofrece_como_boton(client):
    texto = "cómo registro un precio y creo una cuenta"
    principal, relacionado = buscar_temas(texto, limite=2)
    html = _decir(client, texto)
    assert f"<strong>{principal.titulo}</strong>" in html  # responde el más afín
    assert f'name="tema" value="{relacionado.id}"' in html  # el otro, a un toque


def test_el_boton_de_un_tema_responde_sin_ia_y_muestra_la_pregunta(client):
    html = _decir(client, "¿Cómo creo una cuenta?", tema="cuenta")
    assert html.count("¿Cómo creo una cuenta?") >= 2  # lo que tocó + el título de la respuesta
    assert "Crear cuenta" in html and "8 caracteres o más" in html


def test_un_tema_inexistente_no_rompe_el_chat(client):
    html = _decir(client, "hola", tema="no-existe")
    assert "burbuja" in html


def test_el_saludo_invita_a_las_primeras_acciones(client):
    html = client.get(reverse("canasta:inicio")).content.decode()
    assert "¿Primera vez aquí?" in html
    for tema in ("registrar", "comparar", "cuenta", "escanear"):
        assert f'name="tema" value="{tema}"' in html
    assert "lista de ejemplo" not in html


def test_una_lista_de_compras_no_se_confunde_con_una_pregunta_de_ayuda(client):
    html = _decir(client, "2 kg arroz, 1 L leche")
    assert "<strong>¿Cómo" not in html


def test_los_textos_de_la_guia_no_se_publican_con_html_peligroso(client):
    html = _decir(client, "<script>alert(1)</script> cómo registro un precio")
    assert "<script>alert(1)</script>" not in html


# --- con IA: consulta la guía como herramienta --------------------------------------------------
class ModeloFalso:
    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.recibido = []

    def responder(self, *, sistema, mensajes, herramientas):
        self.recibido.append(
            {
                "sistema": sistema,
                "mensajes": json.loads(json.dumps(mensajes)),
                "tools": herramientas,
            }
        )
        return self.respuestas.pop(0)


@pytest.fixture
def ia_activa(settings, monkeypatch):
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ASISTENTE_IA_ACTIVO": True,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
    }

    def instalar(*respuestas):
        falso = ModeloFalso(*respuestas)
        monkeypatch.setattr(integraciones, "crear_asistente", lambda: falso)
        return falso

    return instalar


def _usa_guia(consulta):
    bloque = {
        "type": "tool_use",
        "id": "g1",
        "name": "consultar_guia",
        "input": {"consulta": consulta},
    }
    return RespuestaModelo(parada="tool_use", bloques=[bloque])


def _texto(texto):
    return RespuestaModelo(parada="end_turn", bloques=[{"type": "text", "text": texto}])


def test_la_ia_consulta_la_guia_y_el_sistema_pone_los_botones(client, ia_activa):
    falso = ia_activa(
        _usa_guia("cómo registro un precio"),
        _texto("Toca «Registrar precio», busca el producto y escribe el precio. ¡Es rápido!"),
    )
    html = _decir(client, "no sé cómo subir un precio de la leche")
    assert "Toca «Registrar precio»" in html
    assert 'href="/precios/registrar/"' in html  # el botón lo pone el sistema
    assert "cc-res" not in html  # una pregunta de ayuda no abre la tarjeta de tiendas
    resultado = json.dumps(falso.recibido[1]["mensajes"], ensure_ascii=False)
    assert "Guardar precio" in resultado  # la IA recibió los pasos reales
    assert "consultar_guia" in {t["name"] for t in falso.recibido[0]["tools"]}
    assert "TEMAS DE LA GUÍA" in falso.recibido[0]["sistema"]


def test_si_la_guia_no_cubre_el_tema_la_ia_lo_sabe(client, ia_activa):
    falso = ia_activa(_usa_guia("cómo viajo a la luna"), _texto("Eso no está en mi guía."))
    html = _decir(client, "cómo viajo a la luna")
    assert "Eso no está en mi guía." in html
    assert "La guía no cubre eso" in json.dumps(falso.recibido[1]["mensajes"], ensure_ascii=False)


def test_una_cifra_inventada_en_una_respuesta_de_ayuda_se_descarta(client, ia_activa):
    ia_activa(_usa_guia("cómo registro un precio"), _texto("Es gratis y cuesta $5.000 al mes."))
    html = _decir(client, "cómo subo un precio")
    assert "5.000" not in html  # EC-14


def test_las_preguntas_de_ayuda_con_ia_van_a_la_ia_pero_el_boton_de_tema_no(client, ia_activa):
    falso = ia_activa()  # no debe llamarse: el botón de un tema es gratis
    _decir(client, "¿Cómo creo una cuenta?", tema="cuenta")
    assert falso.recibido == []


def test_los_iconos_de_los_botones_existen_en_el_sprite():
    from pathlib import Path

    sprite = (Path(__file__).resolve().parents[2] / "templates/partials/_iconos.html").read_text()
    for t in TEMAS:
        assert f'id="{t.icono}"' in sprite, (t.id, t.icono)


def test_el_saludo_muestra_atajos_parejos_con_etiqueta_corta(client):
    html = client.get(reverse("canasta:inicio")).content.decode()
    assert html.count('class="atajo"') == 4
    for etiqueta in (
        "Registrar un precio",
        "Comparar precios",
        "Crear una cuenta",
        "Usar la cámara",
    ):
        assert etiqueta in html


def test_al_tocar_un_atajo_la_conversacion_muestra_la_pregunta_completa(client):
    html = _decir(client, "¿Cómo registro un precio?", tema="registrar")
    assert "<strong>¿Cómo registro un precio?</strong>" in html


def test_el_saludo_ofrece_enviar_el_mercado_con_un_enlace_que_lleva_a_la_caja(client):
    html = client.get(reverse("canasta:inicio")).content.decode()
    assert 'href="#chat-mensaje"' in html and "data-enviar-mercado" in html  # funciona sin JS
    assert "Enviar mi mercado" in html


# --- minitutoriales visuales --------------------------------------------------------------------
_CLASE_DE = {
    "boton": "mini-boton",
    "boton_sec": "mini-boton",
    "campo": "mini-campo",
    "buscador": "mini-buscador",
    "opciones": "mini-opciones",
    "filas": "mini-filas",
    "chip": "mini-chip",
    "icono": "mini-icono",
    "simbolo": "mini-icono",
    "casilla": "mini-casilla",
}


def test_la_respuesta_es_un_paso_a_paso_con_una_imagen_en_cada_paso(client):
    html = _decir(client, "¿Cómo registro un precio?")
    assert html.count('class="tuto"') == 1
    assert html.count('class="tuto-paso"') == len(tema_por_id("registrar").pasos)
    assert "mini-boton" in html and "mini-campo" in html and "mini-opciones" in html


def test_las_imagenes_son_decorativas_y_el_texto_de_cada_paso_se_lee(client):
    html = _decir(client, "¿Cómo registro un precio?")
    assert (
        html.count('class="tuto-visual" aria-hidden="true"') >= 4
    )  # lo dibujado no se lee 2 veces
    assert "Paso 1: busca el producto" in html  # el texto real sí (lectores de pantalla)


@pytest.mark.parametrize("tema", [t.id for t in TEMAS])
def test_todos_los_temas_se_dibujan_completos(client, tema):
    guia = tema_por_id(tema)
    html = _decir(client, guia.titulo, tema=tema)
    assert html.count('class="tuto-paso"') == len(guia.pasos)
    for paso in guia.pasos:
        for v in paso.visuales:
            assert _CLASE_DE[v.tipo] in html, (tema, v.tipo)
    assert "Ejemplo ilustrativo" in html  # no se confunde con datos reales


def test_el_mensaje_guarda_el_tema_y_no_la_copia_del_tutorial(client):
    _decir(client, "¿Cómo registro un precio?")
    guardado = client.session["asistente_v1"]["mensajes"][-1]
    assert guardado["tema"] == "registrar" and "pasos" not in guardado


def test_solo_el_ultimo_tutorial_se_dibuja_completo(client):
    _decir(client, "¿Cómo registro un precio?")
    html = _decir(client, "¿Cómo creo una cuenta?")
    assert html.count('class="tuto"') == 2  # los dos siguen visibles en la conversación


def test_con_ia_el_sistema_dibuja_el_tutorial_debajo_de_la_explicacion(client, ia_activa):
    ia_activa(_usa_guia("cómo registro un precio"), _texto("Es rápido: te lo muestro paso a paso."))
    html = _decir(client, "no sé cómo subir un precio")
    assert "Es rápido: te lo muestro paso a paso." in html
    assert html.count('class="tuto"') == 1 and "mini-boton" in html


def test_con_ia_se_le_pide_no_repetir_los_pasos_que_el_sistema_dibuja():
    from apps.integraciones.domain.asistente import INSTRUCCIONES

    assert "no repitas todos los pasos" in INSTRUCCIONES.lower()
