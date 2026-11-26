"""Política de tratamiento de datos (Ley 1581 de 2012): pública y enlazada desde el registro.

ADR-0008 (5) y RNF-17: la política se publica y el titular puede leerla antes de autorizar.
"""

import re

import pytest
from django.test import override_settings
from django.urls import reverse

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def _referencias_rotas(html: str) -> list[str]:
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    citados = re.findall(r'aria-(?:describedby|labelledby|controls)="([^"]+)"', html)
    return sorted({ref for grupo in citados for ref in grupo.split()} - ids)


def _politica(client) -> str:
    return client.get(reverse("cuentas:politica_datos")).content.decode()


def test_la_politica_es_publica_y_no_pide_cuenta(client):
    respuesta = client.get(reverse("cuentas:politica_datos"))
    assert respuesta.status_code == 200
    assert "Política de tratamiento de datos" in respuesta.content.decode()


def test_la_politica_solo_responde_a_get(client):
    assert client.post(reverse("cuentas:politica_datos")).status_code == 405


def test_la_politica_dice_quien_responde_que_se_recoge_y_para_que(client):
    html = _politica(client)
    for tema in (
        "Responsable del tratamiento",
        "Datos que tratamos",
        "Para qué usamos tus datos",
        "Tus derechos",
        "Ley 1581 de 2012",
        "Superintendencia de Industria y Comercio",
    ):
        assert tema in html


def test_la_politica_informa_el_envio_de_la_foto_a_anthropic(client):
    # ADR-022: la foto viaja a un tercero; hay que informarlo para poder usar la función
    html = _politica(client)
    assert "Anthropic" in html
    assert "no se guarda" in html
    assert "1024" in html


def test_la_politica_informa_el_escaneo_en_vivo_con_ia(client):
    # ADR-0026: los cuadros del escáner viajan a Anthropic solo para extraer el texto; es opcional
    html = _politica(client)
    assert "Escaneo en vivo con IA (opcional)" in html
    assert "solo para extraer el texto" in html
    assert "ni la imagen ni los cuadros se guardan" in html


def test_la_politica_no_promete_lo_que_la_plataforma_no_hace(client):
    html = _politica(client)
    assert "No vendemos tus datos" in html
    assert "geolocalización" in html  # aclara que no se almacena la del reportante


def test_la_politica_muestra_el_correo_de_contacto_si_esta_configurado(client):
    with override_settings(POLITICA_DATOS={"RESPONSABLE": "Equipo X", "CORREO_CONTACTO": "d@x.co"}):
        html = _politica(client)
    assert 'href="mailto:d@x.co"' in html
    assert "Equipo X" in html


def test_sin_correo_configurado_no_se_inventa_uno(client):
    with override_settings(POLITICA_DATOS={"RESPONSABLE": "Equipo X", "CORREO_CONTACTO": ""}):
        html = _politica(client)
    assert "mailto:" not in html
    assert reverse("cuentas:mis_datos") in html  # el canal sigue siendo «Mis datos»


def test_la_politica_cumple_lo_basico_de_accesibilidad(client):
    html = _politica(client)
    assert html.count("<h1") == 1
    assert _referencias_rotas(html) == []
    assert 'lang="es-CO"' in html


# ───────────── Enlaces ─────────────


def test_el_registro_enlaza_la_politica_junto_a_la_autorizacion(client):
    html = client.get(reverse("cuentas:registro")).content.decode()
    assert f'href="{reverse("cuentas:politica_datos")}"' in html
    assert "se abre en una pestaña nueva" in html
    assert 'id="id_acepto_tratamiento_datos_helptext"' in html
    assert 'aria-describedby="id_acepto_tratamiento_datos_helptext"' in html
    assert _referencias_rotas(html) == []


def test_el_enlace_del_registro_sigue_ahi_cuando_hay_errores(client):
    html = client.post(reverse("cuentas:registro"), {"username": ""}).content.decode()
    assert f'href="{reverse("cuentas:politica_datos")}"' in html
    assert _referencias_rotas(html) == []


def test_el_pie_de_toda_pagina_enlaza_la_politica(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    pie = html[html.index('<footer class="pie">') :]
    assert f'href="{reverse("cuentas:politica_datos")}"' in pie


def test_por_defecto_la_politica_muestra_el_correo_del_proyecto(client):
    html = _politica(client)
    assert 'href="mailto:ahorrapuescolombia@gmail.com"' in html


# --- el aviso sobre la IA vive en la política de datos, no en las pantallas ---------------------
def test_la_politica_cubre_la_foto_el_escaner_y_k_nasta(client):
    html = client.get(reverse("cuentas:politica_datos")).content.decode()
    for tema in ("Búsqueda por foto", "Escaneo en vivo con IA", "K-nasta, el asistente"):
        assert tema in html
    assert html.count("Anthropic") >= 3


def test_las_pantallas_no_repiten_el_aviso_de_la_ia(client, settings):
    settings.INTEGRACIONES = {
        **settings.INTEGRACIONES,
        "ASISTENTE_IA_ACTIVO": True,
        "ESCANEO_VIVO_ACTIVO": True,
        "ANTHROPIC_API_KEY": "clave-de-prueba",
    }
    inicio = client.get(reverse("comparacion:inicio")).content.decode()
    assert "enviamos a Anthropic" not in inicio and "se envían a Anthropic" not in inicio
    chat = client.get(reverse("canasta:cuerpo")).content.decode()
    assert "Anthropic" not in chat and "No escribas datos personales" not in chat
