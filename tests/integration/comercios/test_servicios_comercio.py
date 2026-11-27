"""Servicios del módulo comercial: perfil, verificación, precio oficial, promociones y
correcciones (RF-C01 a RF-C07, ADR-015). Escritura autenticada, con autor y fecha (M-13, M-14)."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

from apps.comercios import services
from apps.comercios.models import PerfilComercio, PrecioOficial, Promocion, SolicitudCorreccion
from apps.cuentas.services import asegurar_comercio
from apps.notificaciones.models import CorreoPendiente
from tests.integration.comercios.pdf import pdfs

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

MANANA = timedelta(days=1)


def _promo(usuario, presentacion, **extra):
    datos = {
        "usuario": usuario,
        "presentacion_id": presentacion.pk,
        "tipo": "descuento_porcentual",
        "porcentaje": Decimal("10"),
        "inicio": timezone.now() - MANANA,
        "fin": timezone.now() + 7 * MANANA,
        "motivo": "temporada",
        "condiciones": "Hasta agotar existencias.",
    }
    return services.crear_promocion(**(datos | extra))


# ---------- RF-C01: perfil ----------


def test_crear_perfil_queda_pendiente_con_codigo(duena, tiendas):
    perfil = services.crear_perfil(
        usuario=duena,
        establecimiento_id=tiendas[0].pk,
        nombre_contacto="Rosa",
        **pdfs(),
    )
    assert perfil.estado == PerfilComercio.Estado.PENDIENTE
    assert len(perfil.codigo_verificacion) == services.LARGO_CODIGO
    assert perfil.verificado_por is None


def test_un_establecimiento_tiene_un_solo_perfil_activo(duena, crear_usuario, tiendas):
    services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )
    with pytest.raises(ValidationError):
        services.crear_perfil(
            usuario=crear_usuario("otra"),
            establecimiento_id=tiendas[0].pk,
            nombre_contacto="O",
            **pdfs(),
        )


def test_la_bd_tambien_impide_dos_perfiles_activos(duena, crear_usuario, tiendas):
    PerfilComercio.objects.create(
        usuario=duena,
        establecimiento=tiendas[0],
        nombre_contacto="R",
        codigo_verificacion="A",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        PerfilComercio.objects.create(
            usuario=crear_usuario("otra"),
            establecimiento=tiendas[0],
            nombre_contacto="O",
            codigo_verificacion="B",
        )


def test_moderacion_no_puede_crear_un_perfil(moderador, tiendas):
    with pytest.raises(ValidationError):
        services.crear_perfil(
            usuario=moderador, establecimiento_id=tiendas[0].pk, nombre_contacto="M", **pdfs()
        )


def test_solo_establecimientos_aprobados(duena, tiendas):
    local = tiendas[0]
    local.estado, local.activo = "pendiente", False
    local.save()
    with pytest.raises(ValidationError):
        services.crear_perfil(
            usuario=duena, establecimiento_id=local.pk, nombre_contacto="R", **pdfs()
        )


# ---------- RF-C02: verificación (ADR-015) ----------


def test_verificar_asigna_el_rol_guarda_quien_y_cuando_y_avisa(duena, tiendas, moderador):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )
    services.verificar_perfil(moderador=moderador, perfil_id=perfil.pk, aprobar=True)
    perfil.refresh_from_db()
    duena.refresh_from_db()
    assert perfil.estado == PerfilComercio.Estado.VERIFICADO
    assert perfil.verificado_por == moderador and perfil.verificado_en is not None  # M-14
    assert duena.rol == "comercio"
    correo = CorreoPendiente.objects.get(tipo="perfil_verificado")
    assert correo.usuario == duena and correo.contexto["aprobado"] is True


def test_no_verificar_exige_motivo_y_no_cambia_el_rol(duena, tiendas, moderador):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )
    with pytest.raises(ValidationError):
        services.verificar_perfil(moderador=moderador, perfil_id=perfil.pk, aprobar=False)
    services.verificar_perfil(
        moderador=moderador, perfil_id=perfil.pk, aprobar=False, motivo="Sin evidencia"
    )
    duena.refresh_from_db()
    assert duena.rol == "reportante"
    assert PerfilComercio.objects.get(pk=perfil.pk).estado == PerfilComercio.Estado.RECHAZADO


def test_tras_un_rechazo_se_puede_pedir_otra_vez(duena, tiendas, moderador):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )
    services.verificar_perfil(moderador=moderador, perfil_id=perfil.pk, aprobar=False, motivo="x")
    services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )


def test_quien_no_modera_no_verifica(duena, tiendas, crear_usuario):
    perfil = services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )
    with pytest.raises(PermissionDenied):
        services.verificar_perfil(moderador=crear_usuario("x"), perfil_id=perfil.pk, aprobar=True)


def test_un_perfil_ya_decidido_no_se_vuelve_a_decidir(comercio, moderador):
    with pytest.raises(ValidationError):
        services.verificar_perfil(moderador=moderador, perfil_id=comercio.pk, aprobar=True)


def test_asegurar_comercio_nunca_baja_el_rol_de_moderacion(moderador):
    with pytest.raises(ValidationError):
        asegurar_comercio(usuario_id=moderador.pk)


def test_asegurar_comercio_es_idempotente(comercio, duena):
    assert asegurar_comercio(usuario_id=duena.pk).rol == "comercio"


# ---------- RF-C03 y RF-C07: precio oficial ----------


def test_comercio_no_verificado_no_publica(duena, tiendas, arroz):
    services.crear_perfil(
        usuario=duena, establecimiento_id=tiendas[0].pk, nombre_contacto="R", **pdfs()
    )
    with pytest.raises(services.ComercioNoVerificadoError):
        services.publicar_precio_oficial(
            usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal("4000")
        )


def test_publicar_y_actualizar_el_precio_oficial(comercio, duena, arroz):
    services.publicar_precio_oficial(usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(1))
    oficial = services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal("4100")
    )
    assert PrecioOficial.objects.filter(perfil=comercio).count() == 1
    assert oficial.precio == Decimal("4100")


@pytest.mark.parametrize("precio", [Decimal("0"), Decimal("-5")])
def test_el_precio_oficial_debe_ser_positivo(comercio, duena, arroz, precio):
    with pytest.raises(ValidationError):
        services.publicar_precio_oficial(usuario=duena, presentacion_id=arroz[2].pk, precio=precio)


def test_la_bd_rechaza_un_precio_oficial_no_positivo(comercio, arroz):
    with pytest.raises(IntegrityError), transaction.atomic():
        PrecioOficial.objects.create(
            perfil=comercio, presentacion=arroz[2], precio=0, confirmado_en=timezone.now()
        )


def test_confirmar_vigencia_renueva_todos_sus_precios(comercio, duena, arroz):
    for p in arroz[1:]:
        services.publicar_precio_oficial(usuario=duena, presentacion_id=p.pk, precio=Decimal(4000))
    PrecioOficial.objects.update(confirmado_en=timezone.now() - 20 * MANANA)
    assert services.confirmar_vigencia(usuario=duena) == 2
    assert all(
        timezone.now() - p.confirmado_en < timedelta(minutes=1) for p in PrecioOficial.objects.all()
    )


# ---------- RF-C04: promociones ----------


def test_una_promocion_exige_precio_oficial(comercio, duena, arroz):
    with pytest.raises(ValidationError):
        _promo(duena, arroz[2])


def test_crear_promocion_sobre_el_precio_oficial(comercio, duena, arroz):
    services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    promo = _promo(duena, arroz[2])
    assert promo.perfil == comercio and promo.activa


def test_precio_especial_mayor_que_el_regular_se_rechaza(comercio, duena, arroz):
    services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    with pytest.raises(ValidationError):
        _promo(
            duena,
            arroz[2],
            tipo="precio_especial",
            porcentaje=None,
            precio_especial=Decimal("4500"),
        )


def test_proximo_a_vencer_sin_fecha_se_rechaza(comercio, duena, arroz):
    services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    with pytest.raises(ValidationError):
        _promo(duena, arroz[2], motivo="proximo_a_vencer")


def test_la_bd_rechaza_un_descuento_de_cero(comercio, arroz):
    with pytest.raises(IntegrityError), transaction.atomic():
        Promocion.objects.create(
            perfil=comercio,
            presentacion=arroz[2],
            tipo="descuento_porcentual",
            porcentaje=0,
            inicio=timezone.now(),
            fin=timezone.now() + MANANA,
            motivo="temporada",
            condiciones="x",
        )


# ---------- Aislamiento entre comercios ----------


def test_un_comercio_no_termina_la_promocion_de_otro(
    comercio, duena, crear_usuario, tiendas, verificar, arroz
):
    services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    promo = _promo(duena, arroz[2])
    otro = crear_usuario("otro")
    verificar(otro, tiendas[1])
    with pytest.raises(ValidationError):
        services.finalizar_promocion(usuario=otro, promocion_id=promo.pk)
    assert Promocion.objects.get(pk=promo.pk).activa


def test_un_comercio_no_retira_el_precio_de_otro(
    comercio, duena, crear_usuario, tiendas, verificar, arroz
):
    oficial = services.publicar_precio_oficial(
        usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(4000)
    )
    otro = crear_usuario("otro")
    verificar(otro, tiendas[1])
    with pytest.raises(ValidationError):
        services.retirar_precio_oficial(usuario=otro, precio_id=oficial.pk)
    assert PrecioOficial.objects.filter(pk=oficial.pk).exists()


# ---------- RF-C06: correcciones ----------


def test_corregir_un_precio_exige_que_sea_de_su_tienda(comercio, duena, tiendas, arroz, reportar):
    ajeno = reportar(arroz[2], tiendas[1], "5000")
    with pytest.raises(ValidationError):
        services.solicitar_correccion(
            usuario=duena, tipo="precio_reportado", descripcion="No es así", reporte_id=ajeno.pk
        )
    propio = reportar(arroz[2], tiendas[0], "9000")
    solicitud = services.solicitar_correccion(
        usuario=duena, tipo="precio_reportado", descripcion="Vale 4000", reporte_id=propio.pk
    )
    assert solicitud.estado == SolicitudCorreccion.Estado.PENDIENTE


def test_resolver_una_correccion_avisa_al_comercio(comercio, duena, moderador):
    solicitud = services.solicitar_correccion(
        usuario=duena, tipo="datos_establecimiento", descripcion="La dirección cambió"
    )
    services.resolver_correccion(
        moderador=moderador, solicitud_id=solicitud.pk, aceptar=True, respuesta="Actualizada"
    )
    solicitud.refresh_from_db()
    assert solicitud.resuelta_por == moderador and solicitud.resuelta_en is not None  # M-14
    correo = CorreoPendiente.objects.get(tipo="correccion_resuelta")
    assert correo.usuario == duena and correo.contexto["respuesta"] == "Actualizada"


def test_los_correos_salen_por_la_cola_y_no_llevan_el_telefono(comercio, duena):
    # M-15: el contexto persistido del correo no trae datos de contacto del perfil
    correo = CorreoPendiente.objects.get(tipo="perfil_verificado")
    assert "3001234567" not in str(correo.contexto)
    assert len(mail.outbox) <= 1


# ---------- Límite de escrituras (M-16) ----------


@override_settings(COMERCIOS={"ESCRITURAS_POR_HORA": 3})  # crear el perfil cuenta como una
def test_el_comercio_tiene_un_tope_de_escrituras_por_hora(comercio, duena, arroz):
    services.publicar_precio_oficial(usuario=duena, presentacion_id=arroz[1].pk, precio=Decimal(1))
    services.publicar_precio_oficial(usuario=duena, presentacion_id=arroz[2].pk, precio=Decimal(2))
    with pytest.raises(services.LimiteComercioError):
        services.confirmar_vigencia(usuario=duena)
