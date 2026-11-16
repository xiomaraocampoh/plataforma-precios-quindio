"""Accesibilidad WCAG 2.2 AA verificable en el HTML del servidor (M-03)."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse

pytestmark = pytest.mark.integration

CAMPOS_VACIOS_PRECIO = {"establecimiento": "", "presentacion": "", "precio": "", "id_cliente": ""}


def _referencias_rotas(html: str) -> list[str]:
    """IDs citados por aria-describedby/labelledby/controls que no existen en la página."""
    ids = set(re.findall(r'\bid="([^"]+)"', html))
    citados = re.findall(r'aria-(?:describedby|labelledby|controls)="([^"]+)"', html)
    return sorted({ref for grupo in citados for ref in grupo.split()} - ids)


def test_registro_de_cuenta_asocia_ayudas_y_errores_a_sus_campos(client):
    # M-03 · 1.3.1: cada aria-describedby que genera Django debe apuntar a un elemento real
    vacio = client.get(reverse("cuentas:registro")).content.decode()
    con_errores = client.post(
        reverse("cuentas:registro"), {"username": "", "password1": "", "password2": ""}
    ).content.decode()
    assert _referencias_rotas(vacio) == []
    assert _referencias_rotas(con_errores) == []
    assert 'id="id_username_error"' in con_errores
    assert 'id="id_username_helptext"' in con_errores  # la ayuda sigue visible junto al error


def test_registro_de_precio_por_htmx_asocia_errores_a_sus_campos(client, reportante):
    # M-03 · 1.3.1 y 3.3.1, en el fragmento que devuelve HTMX
    client.force_login(reportante)
    html = client.post(
        reverse("precios:registrar"), CAMPOS_VACIOS_PRECIO, HTTP_HX_REQUEST="true"
    ).content.decode()
    assert html.count('aria-invalid="true"') == 3
    assert _referencias_rotas(html) == []


def test_ingreso_con_campos_vacios_muestra_un_error_por_campo(client):
    # M-03 · 3.3.1: antes la página se recargaba sin ningún mensaje
    html = client.post(
        reverse("cuentas:ingresar"), {"username": "", "password": ""}
    ).content.decode()
    assert html.count('aria-invalid="true"') == 2
    assert 'id="id_username_error"' in html
    assert 'id="id_password_error"' in html
    assert _referencias_rotas(html) == []


def test_el_titular_se_anima_menos_de_5_segundos_y_termina_en_su_palabra_inicial(client, db):
    # M-03 · 2.2.2: un movimiento automático que dura ≤ 5 s no necesita control de pausa.
    html = client.get(reverse("comparacion:inicio")).content.decode()
    palabras = re.search(r'data-palabras="([^"]+)"', html).group(1).split(",")
    assert palabras[-1] == palabras[0]  # termina donde empezó: el titular no cambia de sentido
    assert "pausar-rotacion" not in html  # sin control: la animación se detiene sola
    fuente = (Path(settings.BASE_DIR) / "static/js/hero.js").read_text(encoding="utf-8")
    assert "setInterval" not in fuente  # nada corre para siempre
    intervalo = int(re.search(r"INTERVALO_MS = (\d+)", fuente).group(1))
    transicion = 700  # ms que tarda en entrar la última palabra
    assert (len(palabras) - 1) * intervalo + transicion <= 5000


def test_comparacion_permite_pausar_la_actualizacion_automatica(client, db, arroz):
    # M-03 · 2.2.2: la recarga cada 60 s se puede pausar; 4.1.3: sin releer toda la lista
    producto, _, _ = arroz
    html = client.get(reverse("comparacion:comparar", args=[producto.pk])).content.decode()
    assert 'hx-trigger="every 60s [!window.actualizacionPausada]"' in html
    assert re.search(r'<button type="button"[^>]*id="pausar-actualizacion"', html)
    contenedor = re.search(r'<div id="resultados"[^>]*>', html).group(0)
    assert "aria-live" not in contenedor


def test_la_region_de_avisos_existe_antes_de_cualquier_cambio(client, db):
    # M-03 · 4.1.3: la región viva debe estar en la página desde la carga
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert re.search(r'id="avisos" role="status" aria-live="polite"', html)
    assert "js/accesibilidad.js" in html


@pytest.mark.parametrize(
    ("q", "esperado"),
    [
        ("", ""),  # Esc vacía el buscador: la lista se oculta
        ("a", "Escribe al menos dos letras."),
        ("zzz", "No encontramos «zzz». Prueba con otro nombre."),
    ],
)
def test_sugerencias_distinguen_buscador_vacio_corto_y_sin_coincidencias(client, db, q, esperado):
    html = client.get(reverse("comparacion:sugerencias"), {"q": q}).content.decode().strip()
    assert esperado in html if esperado else html == ""
