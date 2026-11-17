"""Correo por la API HTTPS de Brevo (anymail), diagnóstico y reintentos por cron (ADR-021).

Sin red: anymail se simula con su backend de pruebas o con un error lanzado a mano.
"""

import secrets
from datetime import timedelta
from io import StringIO

import pytest
from anymail.exceptions import AnymailAPIError
from django.core import mail
from django.core.cache import cache
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from apps.notificaciones import services
from apps.notificaciones.domain.catalogo import Tipo
from apps.notificaciones.models import CorreoPendiente

pytestmark = pytest.mark.integration
Estado = CorreoPendiente.Estado
URL = "/interno/correos/procesar/"
ANYMAIL_PRUEBA = "anymail.backends.test.EmailBackend"


@pytest.fixture(autouse=True)
def _cache_limpia():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def lucia(django_user_model):
    return django_user_model.objects.create_user(
        username="lucia",
        email="lucia@example.com",
        password="clave-segura-123",
        email_verificado_en=timezone.now(),
    )


@pytest.fixture
def clave():
    return "xkeysib-" + secrets.token_hex(16)  # nunca un literal real


@pytest.fixture
def sin_red(monkeypatch):
    def fallar(self, fail_silently=False):
        raise OSError("sin red")

    monkeypatch.setattr(EmailMultiAlternatives, "send", fallar)
    return monkeypatch


def _encolar(usuario, clave_evento="evento-1", tipo=Tipo.CUENTA_SUSPENDIDA):
    return services.encolar(tipo=tipo, usuario=usuario, clave_idempotencia=clave_evento)


def _listos_para_reintentar():
    CorreoPendiente.objects.update(ultimo_intento=timezone.now() - timedelta(hours=2))


# ---------- envío por anymail ----------


@override_settings(EMAIL_BACKEND=ANYMAIL_PRUEBA, EMAIL_REPLY_TO="r@example.com")
def test_con_anymail_simulado_el_correo_queda_enviado_con_sus_cabeceras(lucia):
    correo = _encolar(lucia)
    correo.refresh_from_db()
    assert correo.estado == Estado.ENVIADO
    enviado = mail.outbox[-1]
    assert enviado.extra_headers["Message-ID"] == correo.message_id
    params = enviado.anymail_test_params  # lo que anymail le habría mandado a Brevo
    assert [str(d) for d in params["reply_to"]] == ["r@example.com"]
    assert params["extra_headers"]["Message-ID"] == correo.message_id


@override_settings(EMAIL_BACKEND=ANYMAIL_PRUEBA)
def test_un_informativo_lleva_list_unsubscribe_por_anymail(lucia, monkeypatch):
    monkeypatch.setattr(services, "_enlace_baja", [lambda usuario: "https://ejemplo.test/baja/x/"])
    correo = services.encolar(
        tipo=Tipo.REPORTE_MODERADO, usuario=lucia, clave_idempotencia="info-1"
    )
    assert correo is not None
    cabeceras = mail.outbox[-1].anymail_test_params["extra_headers"]
    assert cabeceras["List-Unsubscribe"] == "<https://ejemplo.test/baja/x/>"
    assert cabeceras["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_un_anymail_error_deja_el_correo_en_reintento_sin_la_clave(
    lucia, clave, monkeypatch, settings, caplog
):
    settings.BREVO_API_KEY = clave

    def fallar(self, fail_silently=False):
        raise AnymailAPIError(f"Brevo API response 401: Key not found ({clave})")

    monkeypatch.setattr(EmailMultiAlternatives, "send", fallar)
    correo = _encolar(lucia)
    correo.refresh_from_db()
    assert correo.estado == Estado.PENDIENTE and correo.intentos == 1
    assert "AnymailAPIError" in correo.error
    assert clave not in correo.error and clave not in caplog.text


# ---------- POST /interno/correos/procesar/ ----------


def test_el_endpoint_sin_token_o_con_token_errado_responde_403(client, settings, db):
    settings.CORREO_CRON_TOKEN = secrets.token_urlsafe(24)
    assert client.post(URL).status_code == 403
    malo = "Bearer " + secrets.token_urlsafe(24)
    assert client.post(URL, HTTP_AUTHORIZATION=malo).status_code == 403
    sin_bearer = settings.CORREO_CRON_TOKEN
    assert client.post(URL, HTTP_AUTHORIZATION=sin_bearer).status_code == 403


def test_sin_token_configurado_siempre_403(client, settings, db):
    settings.CORREO_CRON_TOKEN = ""
    assert client.post(URL, HTTP_AUTHORIZATION="Bearer ").status_code == 403


def test_con_el_token_correcto_procesa_y_devuelve_solo_conteos(client, settings, lucia, sin_red):
    settings.CORREO_CRON_TOKEN = token = secrets.token_urlsafe(24)
    _encolar(lucia)
    sin_red.undo()  # la red vuelve
    _listos_para_reintentar()
    r = client.post(URL, HTTP_AUTHORIZATION=f"Bearer {token}")
    assert r.status_code == 200
    assert r.json() == {"enviados": 1, "fallidos": 0, "inciertos": 0}
    assert "lucia" not in r.content.decode()


def test_el_endpoint_solo_acepta_post(client, settings, db):
    settings.CORREO_CRON_TOKEN = token = secrets.token_urlsafe(24)
    assert client.get(URL, HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 405


def test_respeta_el_tope_por_pasada(lucia, sin_red):
    for i in range(3):
        _encolar(lucia, clave_evento=f"e{i}")
    sin_red.undo()
    _listos_para_reintentar()
    assert services.enviar_pendientes(limite=2)["enviados"] == 2
    assert CorreoPendiente.objects.filter(estado=Estado.PENDIENTE).count() == 1


# ---------- diagnostico_correo ----------


def test_diagnostico_nunca_imprime_la_clave(settings, clave, db):
    settings.BREVO_API_KEY = clave
    settings.EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    salida = StringIO()
    call_command("diagnostico_correo", stdout=salida)
    texto = salida.getvalue()
    assert clave not in texto
    assert "API HTTPS de Brevo" in texto and "BREVO_API_KEY definida: sí" in texto
    assert "Cola:" in texto


def test_diagnostico_envia_un_correo_de_prueba(db):
    salida = StringIO()
    call_command("diagnostico_correo", "--enviar", "prueba@example.com", stdout=salida)
    assert "Correo de prueba enviado" in salida.getvalue()
    assert mail.outbox[-1].to == ["prueba@example.com"]


def test_diagnostico_informa_el_fallo_sin_la_clave(settings, clave, monkeypatch, db):
    settings.BREVO_API_KEY = clave

    def fallar(self, fail_silently=False):
        raise AnymailAPIError(f"rechazado con {clave}")

    monkeypatch.setattr(EmailMultiAlternatives, "send", fallar)
    with pytest.raises(CommandError) as error:
        call_command("diagnostico_correo", "--enviar", "prueba@example.com", stdout=StringIO())
    assert clave not in str(error.value) and "AnymailAPIError" in str(error.value)


def test_diagnostico_avisa_smtp_en_produccion(settings, db):
    settings.DEBUG = False
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    salida = StringIO()
    call_command("diagnostico_correo", stdout=salida)
    assert "bloquea los puertos" in salida.getvalue()
