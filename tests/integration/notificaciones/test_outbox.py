"""Outbox de correo: un correo por evento, reintentos sin duplicados y sin secretos guardados."""

import logging
from datetime import timedelta
from io import StringIO

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.notificaciones import services
from apps.notificaciones.domain.catalogo import Tipo
from apps.notificaciones.domain.reintentos import espera_tras
from apps.notificaciones.models import CorreoPendiente

pytestmark = pytest.mark.integration
Estado = CorreoPendiente.Estado


@pytest.fixture
def lucia(django_user_model):
    return django_user_model.objects.create_user(
        username="lucia",
        email="lucia@example.com",
        password="clave-segura-123",
        email_verificado_en=timezone.now(),
    )


@pytest.fixture
def smtp_caido(monkeypatch):
    """El relé no responde: cada intento falla como fallaría Brevo sin red."""
    intentos = []

    def fallar(self, fail_silently=False):
        intentos.append(self.to)
        raise ConnectionRefusedError(f"no se pudo conectar para {self.to[0]}")

    monkeypatch.setattr(EmailMultiAlternatives, "send", fallar)
    return intentos


def _encolar(usuario, tipo=Tipo.CUENTA_SUSPENDIDA, clave="evento-1", **extra):
    return services.encolar(tipo=tipo, usuario=usuario, clave_idempotencia=clave, **extra)


def test_un_evento_un_correo_aunque_se_encole_dos_veces(lucia):
    primero = _encolar(lucia)
    segundo = _encolar(lucia)
    assert primero.pk == segundo.pk
    assert len(mail.outbox) == 1
    assert CorreoPendiente.objects.get().estado == Estado.ENVIADO


def test_con_transaccion_sale_solo_al_confirmar(lucia, django_capture_on_commit_callbacks):
    with override_settings(NOTIFICACIONES={"ENVIAR_AL_CONFIRMAR": True}):
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            _encolar(lucia)
            assert len(mail.outbox) == 0  # todavía dentro de la transacción
    assert len(callbacks) == 1
    assert len(mail.outbox) == 1


def test_cabeceras_reply_to_message_id_y_baja_solo_en_informativos(lucia):
    _encolar(lucia, tipo=Tipo.CUENTA_SUSPENDIDA, clave="seguridad")
    _encolar(lucia, tipo=Tipo.BIENVENIDA, clave="informativo")
    seguridad, informativo = mail.outbox
    assert seguridad.reply_to == ["respuestas@ahorrapues.test"]
    assert seguridad.extra_headers["Message-ID"].endswith("@testserver>")
    assert "List-Unsubscribe" not in seguridad.extra_headers
    assert informativo.extra_headers["List-Unsubscribe"].startswith(
        "<http://testserver/cuentas/correo/baja/"
    )
    assert informativo.extra_headers["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert seguridad.from_email == "AhorraPues <no-responder@ahorrapues.test>"


def test_si_falla_queda_en_la_cola_y_se_reintenta_con_espera_creciente(lucia, smtp_caido):
    _encolar(lucia)
    correo = CorreoPendiente.objects.get()
    assert (correo.estado, correo.intentos) == (Estado.PENDIENTE, 1)
    assert "lucia@example.com" not in correo.error  # el error no guarda el correo
    ahora = correo.ultimo_intento
    assert services.enviar_pendientes(ahora + timedelta(seconds=30))["fallidos"] == 0  # espera
    services.enviar_pendientes(ahora + espera_tras(1))
    correo.refresh_from_db()
    assert correo.intentos == 2
    services.enviar_pendientes(correo.ultimo_intento + espera_tras(2))
    correo.refresh_from_db()
    assert (correo.estado, correo.intentos) == (Estado.FALLIDO, 3)
    services.enviar_pendientes(timezone.now() + timedelta(days=1))
    assert len(smtp_caido) == 3  # nunca más de 3 intentos


def test_un_reintento_exitoso_no_duplica(lucia, smtp_caido, monkeypatch):
    _encolar(lucia)
    monkeypatch.undo()  # vuelve la red
    correo = CorreoPendiente.objects.get()
    services.enviar_pendientes(correo.ultimo_intento + espera_tras(1))
    assert services.enviar(correo.pk) is False  # ya enviado: nadie lo reclama otra vez
    services.enviar_pendientes(timezone.now() + timedelta(days=1))
    assert len(mail.outbox) == 1


def test_un_envio_en_curso_incierto_no_se_reintenta(lucia, smtp_caido):
    _encolar(lucia)
    hace_rato = timezone.now() - timedelta(minutes=30)
    CorreoPendiente.objects.update(estado=Estado.ENVIANDO, ultimo_intento=hace_rato)
    assert services.enviar_pendientes()["inciertos"] == 1
    assert CorreoPendiente.objects.get().estado == Estado.FALLIDO


def test_el_codigo_nunca_se_guarda_y_no_se_reenvia_uno_viejo(lucia, smtp_caido):
    _encolar(
        lucia,
        tipo=Tipo.CODIGO_VERIFICACION,
        contexto={"proposito": "ingresar", "codigo": "123456"},
        efimero={"codigo": "123456"},
    )
    correo = CorreoPendiente.objects.get()
    assert "123456" not in str(correo.contexto)
    services.enviar_pendientes(correo.ultimo_intento + espera_tras(1))
    correo.refresh_from_db()
    assert correo.estado == Estado.FALLIDO
    assert "otro" in correo.error  # hay que pedir un código nuevo


def test_un_enlace_firmado_se_regenera_al_reintentar(django_user_model, smtp_caido, monkeypatch):
    nueva = django_user_model.objects.create_user(
        username="nueva", email="nueva@example.com", password="clave-segura-123"
    )  # al crearse sin pasar por el registro no recibe nada todavía
    _encolar(
        nueva,
        tipo=Tipo.VERIFICAR_CORREO,
        efimero={"enlace": "http://testserver/cuentas/verificar-correo/x/"},
    )
    monkeypatch.undo()
    correo = CorreoPendiente.objects.get()
    services.enviar_pendientes(correo.ultimo_intento + espera_tras(1))
    (mensaje,) = mail.outbox
    assert "/cuentas/verificar-correo/" in mensaje.body
    assert "/cuentas/verificar-correo/x/" not in mensaje.body  # enlace nuevo, no el guardado


def test_los_informativos_respetan_la_preferencia_y_el_correo_verificado(lucia, django_user_model):
    lucia.correos_informativos = False
    lucia.save()
    assert _encolar(lucia, tipo=Tipo.BIENVENIDA, clave="a") is None
    assert _encolar(lucia, tipo=Tipo.CUENTA_SUSPENDIDA, clave="b") is not None  # seguridad
    sin_verificar = django_user_model.objects.create_user(
        username="sinverificar", email="s@example.com", password="clave-segura-123"
    )
    assert _encolar(sin_verificar, tipo=Tipo.REPORTE_MODERADO, clave="c") is None
    assert len(mail.outbox) == 1


def test_el_correo_de_supresion_se_redacta_al_enviarse(db):
    services.encolar(
        tipo=Tipo.CUENTA_SUPRIMIDA,
        destinatario="antes@example.com",
        clave_idempotencia="suprimida-1",
        contexto={"nombre": "antes"},
    )
    assert mail.outbox[0].to == ["antes@example.com"]
    correo = CorreoPendiente.objects.get()
    assert correo.destinatario == "" and correo.contexto == {}


def test_los_logs_no_muestran_el_correo_completo(lucia, smtp_caido, caplog):
    with caplog.at_level(logging.INFO, logger="ahorrapues.correo"):
        _encolar(lucia)
    assert caplog.records
    assert "lucia@example.com" not in caplog.text
    assert "l***@e***.com" in caplog.text


def test_comando_enviar_correos_una_pasada_y_continuo(lucia, smtp_caido, monkeypatch):
    _encolar(lucia)
    monkeypatch.undo()
    CorreoPendiente.objects.update(ultimo_intento=timezone.now() - timedelta(hours=1))
    salida = StringIO()
    call_command("enviar_correos", stdout=salida)
    assert "Enviados: 1" in salida.getvalue()
    salida = StringIO()
    call_command(
        "enviar_correos", "--continuo", "--intervalo", "0", "--pasadas", "2", stdout=salida
    )
    assert salida.getvalue().count("Enviados: 0") == 2
    assert len(mail.outbox) == 1
