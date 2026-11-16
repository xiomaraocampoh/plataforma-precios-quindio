"""Correos de la cuenta: verificación (RF-24), seguridad (RF-25) y moderación (RF-26)."""

import re
import time
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core import mail, signing
from django.urls import reverse
from django.utils import timezone

from apps.cuentas import services
from apps.moderacion import services as moderacion
from apps.notificaciones.models import CorreoPendiente
from apps.precios import services as precios
from apps.precios.models import ReportePrecio

pytestmark = pytest.mark.integration
CLAVE = "clave-muy-segura-2026"
REGISTRO = {
    "username": "nueva",
    "email": "nueva@example.com",
    "password1": CLAVE,
    "password2": CLAVE,
    "acepto_tratamiento_datos": "on",
}
CHROME = "Mozilla/5.0 (Windows NT 10.0) Chrome/131.0 Safari/537.36"
IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Version/18.0 Mobile Safari/604.1"


def _enlace(mensaje, ruta: str) -> str:
    return re.search(rf"https?://[^/\s]+({re.escape(ruta)}\S+/)", mensaje.body).group(1)


@pytest.fixture
def verificada(django_user_model):
    return django_user_model.objects.create_user(
        username="lucia",
        email="lucia@example.com",
        password=CLAVE,
        email_verificado_en=timezone.now(),
    )


# ---------- RF-24: verificación del correo ----------


def test_registrarse_con_correo_envia_el_enlace_y_avisa_hasta_confirmar(client, db):
    client.post(reverse("cuentas:registro"), REGISTRO)
    (mensaje,) = mail.outbox
    assert mensaje.subject == "Confirma tu correo en AhorraPues"
    assert mensaje.to == ["nueva@example.com"]
    assert mensaje.alternatives and mensaje.alternatives[0][1] == "text/html"
    assert "Verifica tu correo" in client.get(reverse("comparacion:inicio")).content.decode()

    enlace = _enlace(mensaje, "/cuentas/verificar-correo/")
    assert "Confirmar mi correo" in client.get(enlace).content.decode()  # el GET no la gasta
    assert client.post(enlace).status_code == 302
    usuario = get_user_model().objects.get(username="nueva")
    assert usuario.email_verificado_en is not None
    assert mail.outbox[-1].subject == "Te damos la bienvenida a AhorraPues"
    assert "Verifica tu correo" not in client.get(reverse("comparacion:inicio")).content.decode()

    reutilizado = client.post(enlace)  # un solo uso
    assert reutilizado.status_code == 400 and "ya se usó" in reutilizado.content.decode()
    assert len(mail.outbox) == 2  # la bienvenida no se repite


def test_registrarse_sin_correo_no_envia_nada(client, db):
    client.post(reverse("cuentas:registro"), {**REGISTRO, "email": ""})
    assert mail.outbox == []


def test_el_enlace_de_verificacion_vence_a_las_24_horas(client, db, monkeypatch):
    client.post(reverse("cuentas:registro"), REGISTRO)
    enlace = _enlace(mail.outbox[0], "/cuentas/verificar-correo/")
    ahora = time.time()
    monkeypatch.setattr(signing.time, "time", lambda: ahora + 24 * 3600 + 60)
    r = client.post(enlace)
    assert r.status_code == 400 and "venció" in r.content.decode()


def test_un_enlace_alterado_no_sirve(client, db):
    r = client.post(reverse("cuentas:verificar_correo", args=["no-es-un-token"]))
    assert r.status_code == 400 and "no es válido" in r.content.decode()


def test_el_reenvio_de_la_verificacion_tiene_limite(client, db):
    client.post(reverse("cuentas:registro"), REGISTRO)
    for _ in range(5):
        r = client.post(reverse("cuentas:reenviar_verificacion"), follow=True)
        assert "Si tu correo aún no está confirmado" in r.content.decode()
    assert len(mail.outbox) == 1 + 3  # registro + 3 reenvíos por hora


def test_cambiar_el_correo_pide_confirmarlo_otra_vez(client, verificada):
    client.force_login(verificada)
    client.post(reverse("cuentas:mis_datos"), {"username": "lucia", "email": "otro@example.com"})
    verificada.refresh_from_db()
    assert verificada.email_verificado_en is None
    assert mail.outbox[-1].to == ["otro@example.com"]


# ---------- RF-02 y RF-25: recuperar y «no fui yo» ----------


def test_recuperar_usa_la_plantilla_y_tiene_limite_sin_revelar_nada(client, verificada):
    for _ in range(5):
        r = client.post(reverse("cuentas:recuperar"), {"email": "lucia@example.com"}, follow=True)
        assert "Revisa tu correo" in r.content.decode()
    assert len(mail.outbox) == 3  # 3 por hora para el mismo correo
    assert mail.outbox[0].subject == "Crea una contraseña nueva para AhorraPues"
    assert "#0071e3" in mail.outbox[0].alternatives[0][0]


def test_cambiar_la_contrasena_avisa_y_no_fui_yo_protege_la_cuenta(client, verificada):
    client.force_login(verificada)
    nueva = "otra-clave-segura-2026"
    client.post(
        reverse("cuentas:contrasena"),
        {"old_password": CLAVE, "new_password1": nueva, "new_password2": nueva},
    )
    (aviso,) = mail.outbox
    assert aviso.subject == "Tu contraseña de AhorraPues cambió"
    enlace = _enlace(aviso, "/cuentas/no-fui-yo/")
    assert "Proteger mi cuenta" in client.get(enlace).content.decode()
    r = client.post(enlace)
    assert "Protegimos tu cuenta" in r.content.decode()
    verificada.refresh_from_db()
    assert not verificada.has_usable_password()
    assert mail.outbox[-1].subject == "Crea una contraseña nueva para AhorraPues"
    assert client.post(enlace).status_code == 400  # ya no sirve


def test_restablecer_la_contrasena_tambien_avisa(client, verificada):
    client.post(reverse("cuentas:recuperar"), {"email": "lucia@example.com"})
    enlace = _enlace(mail.outbox[0], "/cuentas/contrasena/restablecer/")
    formulario = client.get(enlace, follow=True)
    nueva = "otra-clave-segura-2026"
    client.post(formulario.redirect_chain[-1][0], {"new_password1": nueva, "new_password2": nueva})
    assert mail.outbox[-1].subject == "Tu contraseña de AhorraPues cambió"


# ---------- RF-25: dispositivo nuevo ----------


def _ingresar(client, agente, ip="203.0.113.10"):
    return client.post(
        reverse("cuentas:ingresar"),
        {"username": "lucia", "password": CLAVE},
        HTTP_USER_AGENT=agente,
        REMOTE_ADDR=ip,
    )


def test_avisa_del_ingreso_desde_un_dispositivo_nuevo(client, verificada):
    _ingresar(client, CHROME)
    assert mail.outbox == []  # el primer dispositivo de la cuenta no se avisa
    client.post(reverse("cuentas:salir"))
    _ingresar(client, CHROME, ip="203.0.113.99")  # misma red /24: el mismo dispositivo
    assert mail.outbox == []
    client.post(reverse("cuentas:salir"))
    _ingresar(client, IPHONE)
    (aviso,) = mail.outbox
    assert aviso.subject == "Nuevo ingreso a tu cuenta de AhorraPues"
    assert "Safari en iPhone" in aviso.body
    assert "203.0.113" not in aviso.body  # ni la IP ni su red


# ---------- RF-22 y RF-03: suspensión y supresión ----------


def test_suspender_desde_el_panel_avisa(client, verificada, django_user_model):
    admin = django_user_model.objects.create_user(
        username="adm", password="x-clave-1234", rol="administrador"
    )
    services.cambiar_estado_cuenta(actor=admin, usuario_id=verificada.pk, activa=False)
    assert mail.outbox[-1].subject == "Suspendimos tu cuenta de AhorraPues"


def test_suprimir_avisa_a_la_direccion_anterior_y_no_la_guarda(client, verificada):
    client.force_login(verificada)
    client.post(reverse("cuentas:suprimir"), {"password": CLAVE, "confirmo": "on"})
    (aviso,) = mail.outbox
    assert aviso.to == ["lucia@example.com"]
    assert aviso.subject == "Suprimimos tu cuenta de AhorraPues"
    assert not CorreoPendiente.objects.filter(destinatario__icontains="lucia").exists()


# ---------- Ley 1581: preferencias y baja ----------


def test_apagar_los_informativos_en_mis_datos(client, verificada):
    client.force_login(verificada)
    html = client.get(reverse("cuentas:mis_datos")).content.decode()
    assert 'id="preferencias"' in html
    client.post(reverse("cuentas:preferencias"), {})  # casilla desmarcada
    verificada.refresh_from_db()
    assert verificada.correos_informativos is False


def test_el_enlace_de_baja_funciona_sin_sesion_y_con_un_clic(client, verificada):
    enlace = services.correo.enlace_baja(verificada).replace("http://testserver", "")
    assert "Dejar de recibir" in client.get(enlace).content.decode()
    r = client.post(enlace)  # List-Unsubscribe-Post: sin CSRF ni sesión
    assert r.status_code == 200
    verificada.refresh_from_db()
    assert verificada.correos_informativos is False


# ---------- RF-26: resultados de moderación ----------


def test_resultados_de_moderacion_sin_revelar_quien(verificada, arroz, tiendas, django_user_model):
    moderadora = django_user_model.objects.create_user(
        username="moderadora_secreta", password="x-clave-1234", rol="moderador"
    )
    denunciante = django_user_model.objects.create_user(
        username="vecina_que_denuncia",
        email="vecina@example.com",
        password="x-clave-1234",
        email_verificado_en=timezone.now(),
    )
    reporte = precios.registrar_reporte(
        autor=verificada,
        presentacion_id=arroz[1].pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal(2600),
    )
    ReportePrecio.objects.filter(pk=reporte.pk).update(estado=ReportePrecio.Estado.EN_REVISION)
    moderacion.decidir_reporte(moderador=moderadora, reporte_id=reporte.pk, aprobar=True)
    denuncia = moderacion.denunciar(
        denunciante=denunciante, reporte_id=reporte.pk, motivo="precio_falso"
    )
    moderacion.resolver_denuncia(moderador=moderadora, denuncia_id=denuncia.pk, aceptar=False)

    al_autor, a_la_denunciante = mail.outbox
    assert al_autor.to == ["lucia@example.com"]
    assert al_autor.subject == "Tu precio ya está publicado"
    assert "$2.600" in al_autor.body
    assert a_la_denunciante.to == ["vecina@example.com"]
    assert a_la_denunciante.subject == "Revisamos el precio que denunciaste"
    for mensaje in mail.outbox:
        contenido = mensaje.body + mensaje.alternatives[0][0]
        assert "moderadora_secreta" not in contenido
        assert "vecina_que_denuncia" not in contenido


def test_la_moderacion_repetida_no_duplica_el_aviso(verificada, arroz, tiendas, django_user_model):
    moderadora = django_user_model.objects.create_user(
        username="mod", password="x-clave-1234", rol="moderador"
    )
    reporte = precios.registrar_reporte(
        autor=verificada,
        presentacion_id=arroz[1].pk,
        establecimiento_id=tiendas[0].pk,
        precio=Decimal(2600),
    )
    ReportePrecio.objects.filter(pk=reporte.pk).update(estado=ReportePrecio.Estado.EN_REVISION)
    moderacion.decidir_reporte(moderador=moderadora, reporte_id=reporte.pk, aprobar=False)
    with pytest.raises(Exception):  # noqa: B017  ya resuelto: el servicio lo rechaza
        moderacion.decidir_reporte(moderador=moderadora, reporte_id=reporte.pk, aprobar=False)
    assert len(mail.outbox) == 1
