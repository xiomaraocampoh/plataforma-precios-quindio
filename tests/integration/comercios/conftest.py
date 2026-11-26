"""Fixtures del módulo comercial: moderador, dueños y comercios ya verificados por el servicio."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.comercios import services
from apps.precios.models import ReportePrecio


@pytest.fixture
def moderador(django_user_model):
    return django_user_model.objects.create_user(
        username="mod1",
        password="clave-segura-123",
        rol="moderador",
        is_staff=True,
        acepto_tratamiento_datos=True,
    )


@pytest.fixture
def crear_usuario(django_user_model):
    def crear(nombre: str, **extra):
        return django_user_model.objects.create_user(
            username=nombre,
            password="clave-segura-123",
            email=f"{nombre}@example.com",
            email_verificado_en=timezone.now(),
            acepto_tratamiento_datos=True,
            **extra,
        )

    return crear


@pytest.fixture
def duena(crear_usuario):
    return crear_usuario("rosa")


@pytest.fixture
def verificar(moderador):
    """Crea el perfil con el servicio y lo verifica como lo haría moderación."""

    def hacer(usuario, local):
        perfil = services.crear_perfil(
            usuario=usuario,
            establecimiento_id=local.pk,
            nombre_contacto="Rosa",
            telefono="3001234567",
            evidencia="NIT 900123456-7",
        )
        services.verificar_perfil(moderador=moderador, perfil_id=perfil.pk, aprobar=True)
        usuario.refresh_from_db()
        return perfil

    return hacer


@pytest.fixture
def comercio(duena, tiendas, verificar):
    """Tienda Doña Rosa verificada; su dueña ya tiene el rol «comercio»."""
    return verificar(duena, tiendas[0])


@pytest.fixture
def reportar(reportante):
    def hacer(presentacion, local, precio, *, dias=0, autor=None):
        return ReportePrecio.objects.create(
            presentacion=presentacion,
            establecimiento=local,
            autor=autor or reportante,
            precio=Decimal(precio),
            fecha_observacion=timezone.now() - timedelta(days=dias),
        )

    return hacer
