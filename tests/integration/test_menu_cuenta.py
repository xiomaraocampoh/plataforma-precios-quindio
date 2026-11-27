"""La barra y el menú ☰ ofrecen exactamente los mismos enlaces de cuenta (una sola lista)."""

import re

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def _hrefs(bloque: str) -> list[str]:
    return re.findall(r'href="([^"]+)"', bloque)


def _bloques(html: str) -> tuple[str, str]:
    escritorio = html.split('<details class="menu-cuenta">')[1].split("</details>")[0]
    movil = html.split('class="nav-cuenta"')[1].split("</nav>")[0]
    return escritorio, movil


def test_el_menu_de_celular_tiene_los_mismos_enlaces_que_el_desplegable(client, reportante):
    client.force_login(reportante)
    escritorio, movil = _bloques(client.get(reverse("comparacion:inicio")).content.decode())
    assert _hrefs(escritorio) == _hrefs(movil) and len(_hrefs(movil)) >= 3
    for texto in ("Mis aportes", "Mis datos", "Seguridad", "Salir"):
        assert texto in escritorio and texto in movil


def test_con_otro_rol_los_enlaces_siguen_siendo_los_mismos(client, django_user_model):
    moderador = django_user_model.objects.create_user(
        username="mod1",
        password="clave-segura-123",
        rol="moderador",
        is_staff=True,
        acepto_tratamiento_datos=True,
    )
    client.force_login(moderador)
    escritorio, movil = _bloques(client.get(reverse("comparacion:inicio")).content.decode())
    assert reverse("moderacion:bandeja") in _hrefs(movil)
    assert _hrefs(escritorio) == _hrefs(movil)


def test_salir_en_el_menu_es_un_formulario_post_con_csrf(client, reportante):
    client.force_login(reportante)
    _, movil = _bloques(client.get(reverse("comparacion:inicio")).content.decode())
    assert 'method="post"' in movil and "csrfmiddlewaretoken" in movil
    assert f'action="{reverse("cuentas:salir")}"' in movil


def test_sin_sesion_no_hay_menu_de_cuenta(client):
    html = client.get(reverse("comparacion:inicio")).content.decode()
    assert "nav-cuenta" not in html.split("</header>")[0] and "menu-cuenta" not in html
