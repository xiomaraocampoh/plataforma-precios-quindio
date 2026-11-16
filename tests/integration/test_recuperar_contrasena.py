"""RF-02: recuperación de la contraseña por correo con enlace de un solo uso."""

import re

import pytest
from django.core import mail
from django.urls import reverse

pytestmark = pytest.mark.integration

NUEVA = "otra-clave-muy-segura-2026"


@pytest.fixture
def con_correo(django_user_model):
    return django_user_model.objects.create_user(
        username="lucia", email="lucia@example.com", password="clave-inicial-segura-1"
    )


def _enlace(cuerpo: str) -> str:
    return re.search(r"https?://[^/]+(/cuentas/contrasena/restablecer/\S+/)", cuerpo).group(1)


def test_envia_un_enlace_y_permite_cambiar_la_contrasena_una_sola_vez(client, con_correo):
    r = client.post(reverse("cuentas:recuperar"), {"email": "lucia@example.com"})
    assert r.status_code == 302
    assert len(mail.outbox) == 1
    enlace = _enlace(mail.outbox[0].body)

    formulario = client.get(enlace, follow=True)  # Django redirige a la URL con el token en sesión
    assert "Crea una contraseña nueva" in formulario.content.decode()
    r = client.post(
        formulario.redirect_chain[-1][0], {"new_password1": NUEVA, "new_password2": NUEVA}
    )
    assert r.status_code == 302
    con_correo.refresh_from_db()
    assert con_correo.check_password(NUEVA)

    reutilizado = client.get(enlace, follow=True).content.decode()  # enlace de un solo uso
    assert "El enlace ya no es válido" in reutilizado


def test_un_correo_desconocido_no_revela_si_la_cuenta_existe(client, db):
    r = client.post(reverse("cuentas:recuperar"), {"email": "nadie@example.com"}, follow=True)
    assert "Revisa tu correo" in r.content.decode()
    assert len(mail.outbox) == 0


def test_el_ingreso_enlaza_a_la_recuperacion(client, db):
    html = client.get(reverse("cuentas:ingresar")).content.decode()
    assert reverse("cuentas:recuperar") in html
