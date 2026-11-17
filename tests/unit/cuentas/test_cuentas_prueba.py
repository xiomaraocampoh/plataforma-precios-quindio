"""Cuentas de prueba por rol y la excepción local al segundo factor. Dominio puro."""

import pytest

from apps.cuentas.domain.cuentas_prueba import (
    CUENTAS_PRUEBA,
    ContrasenaDePruebaAusenteError,
    exigir_contrasena_de_prueba,
)
from apps.cuentas.domain.segundo_factor import omitir_segundo_factor_de_prueba

pytestmark = pytest.mark.unit


def _por_usuario():
    return {c.usuario: c for c in CUENTAS_PRUEBA}


class TestCatalogoDeCuentas:
    def test_hay_una_cuenta_por_rol_pedido(self):
        cuentas = _por_usuario()
        assert set(cuentas) == {
            "admin_prueba",
            "moderador_prueba",
            "editor_prueba",
            "reportante_prueba",
            "reportante_ana",
            "reportante_luis",
            "comercio_prueba",
            "suspendido_prueba",
        }
        assert cuentas["admin_prueba"].rol == "administrador"
        assert cuentas["moderador_prueba"].rol == "moderador"
        assert cuentas["editor_prueba"].rol == "editor_catalogo"
        assert cuentas["comercio_prueba"].rol == "comercio"
        assert {cuentas[u].rol for u in ("reportante_ana", "reportante_luis")} == {"reportante"}

    def test_solo_el_administrador_es_superusuario(self):
        assert [c.usuario for c in CUENTAS_PRUEBA if c.superusuario] == ["admin_prueba"]

    def test_staff_solo_para_administracion_y_moderacion(self):
        staff = {c.usuario for c in CUENTAS_PRUEBA if c.staff}
        assert staff == {"admin_prueba", "moderador_prueba"}

    def test_solo_la_cuenta_suspendida_queda_inactiva(self):
        assert [c.usuario for c in CUENTAS_PRUEBA if not c.activa] == ["suspendido_prueba"]

    def test_correos_de_ejemplo_nombre_mas_rol(self):
        for cuenta in CUENTAS_PRUEBA:
            local, dominio = cuenta.correo.split("@")
            assert dominio == "example.com"  # RFC 2606: nunca llega a una persona real
            assert local.endswith(f"+{cuenta.rol}")

    def test_cada_cuenta_dice_que_se_puede_probar(self):
        assert all(c.puede_probar.strip() for c in CUENTAS_PRUEBA)


class TestContrasena:
    def test_se_usa_la_variable_de_entorno(self):
        assert exigir_contrasena_de_prueba("una-clave-larga") == "una-clave-larga"

    @pytest.mark.parametrize("valor", [None, "", "   "])
    def test_sin_variable_se_detiene_sin_generar_nada(self, valor):
        with pytest.raises(ContrasenaDePruebaAusenteError, match="CUENTAS_PRUEBA_PASSWORD"):
            exigir_contrasena_de_prueba(valor)


class TestOmitirSegundoFactor:
    @pytest.mark.parametrize(
        ("permitido", "debug", "de_prueba", "omite"),
        [
            (True, True, True, True),  # el único caso: ajuste + DEBUG + cuenta de prueba
            (True, False, True, False),  # en producción (DEBUG=False) nunca
            (False, True, True, False),  # sin el ajuste, nunca
            (True, True, False, False),  # una cuenta real nunca se salta el 2FA
            (False, False, False, False),
        ],
    )
    def test_tabla_de_verdad(self, permitido, debug, de_prueba, omite):
        assert (
            omitir_segundo_factor_de_prueba(
                permitido=permitido, debug=debug, es_cuenta_de_prueba=de_prueba
            )
            is omite
        )
