"""Qué backend de correo se elige según el entorno (ADR-021): Render bloquea SMTP."""

import pytest

from core.correo import ANYMAIL_BREVO, CONSOLA, SMTP, elegir_backend_correo

pytestmark = pytest.mark.unit
LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@pytest.mark.parametrize(
    ("brevo", "host", "explicito", "esperado"),
    [
        ("xkeysib-algo", "", "", ANYMAIL_BREVO),
        ("xkeysib-algo", "smtp-relay.brevo.com", SMTP, ANYMAIL_BREVO),  # la API gana a SMTP
        ("", "smtp-relay.brevo.com", "", SMTP),
        ("", "smtp-relay.brevo.com", SMTP, SMTP),
        ("", "", SMTP, CONSOLA),  # SMTP sin servidor: a la consola
        ("", "", "", CONSOLA),
        ("   ", "", "", CONSOLA),
        ("", "", LOCMEM, LOCMEM),
    ],
)
def test_elige_el_backend(brevo, host, explicito, esperado):
    elegido = elegir_backend_correo(brevo_api_key=brevo, email_host=host, explicito=explicito)
    assert elegido == esperado
