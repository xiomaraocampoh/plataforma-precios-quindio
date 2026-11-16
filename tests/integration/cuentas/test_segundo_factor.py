"""Verificación en dos pasos (RF-27): correo, app TOTP, respaldo, bloqueo, confianza y API."""

import logging
import re
from datetime import timedelta

import pyotp
import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.cuentas.models import SegundoFactor
from apps.cuentas.services import segundo_factor as sf
from apps.cuentas.views.ingreso import FLAG

pytestmark = pytest.mark.integration
CLAVE = "clave-muy-segura-2026"


def _usuario(django_user_model, username="lucia", **extra):
    datos = {"email": f"{username}@example.com", "email_verificado_en": timezone.now(), **extra}
    return django_user_model.objects.create_user(username=username, password=CLAVE, **datos)


def _ingresar(client, username="lucia"):
    return client.post(reverse("cuentas:ingresar"), {"username": username, "password": CLAVE})


def _codigo_del_correo() -> str:
    return re.search(r"^\s+(\d{6})\s*$", mail.outbox[-1].body, re.M).group(1)


def _verificar(client, **datos):
    return client.post(reverse("cuentas:ingresar_verificar"), datos)


def _sesion_abierta(client) -> bool:
    return "_auth_user_id" in client.session


@pytest.fixture
def con_correo(django_user_model):
    usuario = _usuario(django_user_model)
    sf.activar_correo(usuario)
    return usuario


@pytest.fixture
def con_app(django_user_model):
    usuario = _usuario(django_user_model)
    secreto = pyotp.random_base32()
    codigos = sf.activar_app(usuario, secreto=secreto, codigo=pyotp.TOTP(secreto).now())
    return usuario, secreto, codigos


def test_un_reportante_sin_2fa_ingresa_directo(client, django_user_model):
    _usuario(django_user_model)
    _ingresar(client)
    assert _sesion_abierta(client)
    assert client.session[FLAG] == "no_requerido"


# ---------- Código por correo ----------


def test_codigo_por_correo_abre_la_sesion_solo_tras_verificar(client, con_correo):
    r = _ingresar(client)
    assert r["Location"] == reverse("cuentas:ingresar_verificar")
    assert not _sesion_abierta(client)  # ni la web ni la API ven una sesión todavía
    pantalla = client.get(reverse("cuentas:ingresar_verificar")).content.decode()
    assert "Verificación en dos pasos" in pantalla
    assert 'inputmode="numeric"' in pantalla and 'autocomplete="one-time-code"' in pantalla
    assert "Confiar en este dispositivo 30 días" in pantalla
    assert "l***@e***.com" in pantalla  # el correo, enmascarado
    codigo = _codigo_del_correo()
    assert codigo not in SegundoFactor.objects.get(usuario=con_correo).codigo_hash  # solo hash
    assert _verificar(client, codigo=codigo).status_code == 302
    assert _sesion_abierta(client) and client.session[FLAG] == "verificado"


def test_el_codigo_por_correo_sirve_una_vez(client, con_correo):
    _ingresar(client)
    codigo = _codigo_del_correo()
    _verificar(client, codigo=codigo)
    client.post(reverse("cuentas:salir"))
    _ingresar(client)
    r = _verificar(client, codigo=codigo)
    assert "no es correcto" in r.content.decode()


def test_el_codigo_vence_a_los_diez_minutos(client, con_correo):
    _ingresar(client)
    codigo = _codigo_del_correo()
    SegundoFactor.objects.filter(usuario=con_correo).update(
        codigo_vence_en=timezone.now() - timedelta(seconds=1)
    )
    assert "venció" in _verificar(client, codigo=codigo).content.decode()
    assert not _sesion_abierta(client)


def test_cinco_fallos_bloquean_quince_minutos(client, con_correo):
    _ingresar(client)
    codigo = _codigo_del_correo()
    for _ in range(5):
        r = _verificar(client, codigo="000000" if codigo != "000000" else "111111")
    assert "espera 15 minutos" in r.content.decode()
    assert "espera 15 minutos" in _verificar(client, codigo=codigo).content.decode()
    assert not _sesion_abierta(client)
    SegundoFactor.objects.filter(usuario=con_correo).update(
        bloqueado_hasta=timezone.now() - timedelta(seconds=1)
    )
    _verificar(client, codigo=codigo)
    assert _sesion_abierta(client)


def test_el_envio_de_codigos_tiene_limite(client, con_correo):
    _ingresar(client)  # 1.er código
    for _ in range(4):
        r = client.post(reverse("cuentas:ingresar_codigo"), follow=True)
        assert "Si tu cuenta tiene un correo" in r.content.decode()
    assert len(mail.outbox) == 3  # máximo 3 cada 10 minutos


def test_el_codigo_no_aparece_en_los_logs(client, con_correo, caplog):
    with caplog.at_level(logging.DEBUG):
        _ingresar(client)
    codigo = _codigo_del_correo()
    assert codigo not in caplog.text
    assert "lucia@example.com" not in caplog.text


# ---------- App autenticadora (TOTP) ----------


def test_activar_la_app_pide_contrasena_y_muestra_qr_y_respaldo(client, django_user_model):
    usuario = _usuario(django_user_model)
    client.force_login(usuario)
    html = client.get(reverse("cuentas:configurar_app")).content.decode()
    assert "<svg" in html and "Configura tu app autenticadora" in html
    secreto = client.session["ap_totp_nuevo"]
    malo = client.post(
        reverse("cuentas:configurar_app"),
        {"password": "otra", "codigo": pyotp.TOTP(secreto).now()},
    )
    assert "contraseña no es correcta" in malo.content.decode()
    r = client.post(
        reverse("cuentas:configurar_app"),
        {"password": CLAVE, "codigo": pyotp.TOTP(secreto).now()},
    )
    html = r.content.decode()
    assert "Guarda tus códigos de respaldo" in html
    assert len(re.findall(r"<code>[2-9a-z]{4}-[2-9a-z]{4}</code>", html)) == 10
    assert SegundoFactor.objects.get(usuario=usuario).metodo == "app"


def test_ingresar_con_la_app_y_un_codigo_no_se_reutiliza(client, con_app):
    _, secreto, _ = con_app
    _ingresar(client)
    assert mail.outbox == []  # con app no se envía correo
    codigo = pyotp.TOTP(secreto).now()
    _verificar(client, codigo=codigo)
    assert _sesion_abierta(client)
    client.post(reverse("cuentas:salir"))
    _ingresar(client)
    assert "no es correcto" in _verificar(client, codigo=codigo).content.decode()


def test_codigo_de_respaldo_de_un_solo_uso(client, con_app):
    _, _, codigos = con_app
    _ingresar(client)
    _verificar(client, respaldo=codigos[0].upper())
    assert _sesion_abierta(client)
    client.post(reverse("cuentas:salir"))
    _ingresar(client)
    assert "no es correcto" in _verificar(client, respaldo=codigos[0]).content.decode()
    assert sf.respaldo_disponibles(con_app[0]) == 9


# ---------- Dispositivo de confianza ----------


def test_confiar_en_el_dispositivo_30_dias_y_olvidarlo(client, con_app):
    usuario, secreto, _ = con_app
    _ingresar(client)
    r = _verificar(client, codigo=pyotp.TOTP(secreto).now(), confiar="on")
    cookie = r.cookies[sf.COOKIE_CONFIANZA]
    assert cookie["httponly"] and int(cookie["max-age"]) == 30 * 86400
    client.post(reverse("cuentas:salir"))
    _ingresar(client)
    assert _sesion_abierta(client)  # sin segundo paso en este dispositivo
    sf.olvidar_dispositivos(usuario)
    client.post(reverse("cuentas:salir"))
    r = _ingresar(client)
    assert r["Location"] == reverse("cuentas:ingresar_verificar")


def test_una_cookie_de_confianza_alterada_no_sirve(client, con_app):
    client.cookies[sf.COOKIE_CONFIANZA] = "inventada"
    r = _ingresar(client)
    assert r["Location"] == reverse("cuentas:ingresar_verificar")


# ---------- Obligatoria para moderación y staff ----------


def test_un_moderador_siempre_pasa_por_el_segundo_paso(client, django_user_model):
    _usuario(django_user_model, "moderadora", rol="moderador")
    r = _ingresar(client, "moderadora")
    assert r["Location"] == reverse("cuentas:ingresar_verificar")
    assert len(mail.outbox) == 1  # código por correo aunque no lo haya activado


def test_staff_sin_correo_ni_app_configura_la_app_para_entrar(client, django_user_model):
    django_user_model.objects.create_user(username="staff1", password=CLAVE, is_staff=True)
    r = _ingresar(client, "staff1")
    assert r["Location"] == reverse("cuentas:ingresar_configurar")
    html = client.get(r["Location"]).content.decode()
    assert "Tu rol exige la verificación en dos pasos" in html
    secreto = client.session["ap_totp_nuevo"]
    r = client.post(r["Location"], {"codigo": pyotp.TOTP(secreto).now()})
    assert "Guarda tus códigos de respaldo" in r.content.decode()
    assert _sesion_abierta(client) and client.session[FLAG] == "verificado"


def test_el_moderador_no_puede_desactivarla(client, django_user_model):
    moderadora = _usuario(django_user_model, "moderadora", rol="moderador")
    client.force_login(moderadora)
    r = client.post(reverse("cuentas:seguridad"), {"password": CLAVE, "accion": "desactivar"})
    assert "puedes cambiar de método, no quitarla" in r.content.decode()


def test_una_sesion_sin_segundo_factor_se_cierra(client, django_user_model):
    moderadora = _usuario(django_user_model, "moderadora", rol="moderador")
    client.force_login(moderadora)
    sesion = client.session
    del sesion[FLAG]
    sesion.save()
    r = client.get(reverse("moderacion:bandeja"))
    assert r.status_code == 302 and r["Location"].startswith(reverse("cuentas:ingresar"))
    assert not _sesion_abierta(client)


def test_la_api_tambien_exige_el_segundo_factor(client, django_user_model):
    moderadora = _usuario(django_user_model, "moderadora", rol="moderador")
    client.force_login(moderadora)
    assert client.get("/api/v1/catalogo/productos/").status_code == 200  # con 2FA
    sesion = client.session
    sesion[FLAG] = "no_requerido"  # p. ej. recibió el rol después de ingresar
    sesion.save()
    r = client.get("/api/v1/catalogo/productos/")
    assert r.status_code == 401
    assert "verificación en dos pasos" in r.json()["detail"]


def test_el_ingreso_a_admin_pasa_por_el_de_la_plataforma(client, db):
    r = client.get("/admin/login/?next=/admin/")
    assert r.status_code == 302
    assert r["Location"] == f"{reverse('cuentas:ingresar')}?next=/admin/"


def test_activar_por_correo_exige_correo_confirmado(client, django_user_model):
    sin_confirmar = _usuario(django_user_model, "pedro", email_verificado_en=None)
    client.force_login(sin_confirmar)
    r = client.post(reverse("cuentas:seguridad"), {"password": CLAVE, "accion": "correo"})
    assert "Primero confirma tu correo" in r.content.decode()


def test_las_pantallas_de_seguridad_son_accesibles(client, con_correo):
    from tests.integration.panel.conftest import controles_sin_etiqueta, referencias_rotas

    _ingresar(client)
    for html in [
        client.get(reverse("cuentas:ingresar_verificar")).content.decode(),
    ]:
        assert controles_sin_etiqueta(html) == [] and referencias_rotas(html) == []
    _verificar(client, codigo=_codigo_del_correo())
    for url in [reverse("cuentas:seguridad"), reverse("cuentas:configurar_app")]:
        html = client.get(url).content.decode()
        assert controles_sin_etiqueta(html) == [], url
        assert referencias_rotas(html) == [], url
