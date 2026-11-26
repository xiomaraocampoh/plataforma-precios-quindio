"""Cuentas de prueba por rol y la excepción local al segundo factor. Dominio puro."""

import secrets

import pytest

from apps.cuentas.domain.cuentas_prueba import (
    CUENTAS_PRUEBA,
    VARIABLE_CORREO_BASE,
    ContrasenaDePruebaAusenteError,
    CorreoBaseInvalidoError,
    correo_de_prueba,
    correos_de_prueba,
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


class TestCorreoBase:
    """CUENTAS_PRUEBA_CORREO_BASE: los códigos del 2FA llegan a un buzón real del equipo."""

    SUFIJOS = {
        "admin_prueba": "admin",
        "moderador_prueba": "moderador",
        "editor_prueba": "editor",
        "reportante_prueba": "reportante",
        "reportante_ana": "ana",
        "reportante_luis": "luis",
        "comercio_prueba": "comercio",
        "suspendido_prueba": "suspendido",
    }

    def test_cada_cuenta_tiene_su_sufijo(self):
        assert {c.usuario: c.sufijo for c in CUENTAS_PRUEBA} == self.SUFIJOS

    def test_base_valida_usa_parte_local_mas_sufijo(self):
        correos = correos_de_prueba("equipo@correo.test")
        assert correos == {u: f"equipo+{s}@correo.test" for u, s in self.SUFIJOS.items()}

    def test_base_con_espacios_alrededor_se_recorta(self):
        admin = _por_usuario()["admin_prueba"]
        assert correo_de_prueba(admin, "  equipo@correo.test 	") == "equipo+admin@correo.test"

    @pytest.mark.parametrize("base", [None, "", "   "])
    def test_base_vacia_conserva_los_de_example_com(self, base):
        assert correos_de_prueba(base) == {c.usuario: c.correo for c in CUENTAS_PRUEBA}
        assert all(c.endswith("@example.com") for c in correos_de_prueba(base).values())

    def test_base_sin_arroba_da_un_error_claro(self):
        with pytest.raises(CorreoBaseInvalidoError, match=VARIABLE_CORREO_BASE) as error:
            correos_de_prueba("equipo.correo.test")
        assert "parte_local@dominio" in str(error.value)

    @pytest.mark.parametrize(
        "base",
        [
            "@correo.test",  # sin parte local
            "equipo@",  # sin dominio
            "equipo@@correo.test",
            "a@b@correo.test",
            "equipo@correo",  # dominio sin punto
            "equi po@correo.test",
            "equipo+otro@correo.test",  # ya trae etiqueta: el sufijo quedaría ambiguo
        ],
    )
    def test_bases_mal_formadas_se_rechazan(self, base):
        with pytest.raises(CorreoBaseInvalidoError, match=VARIABLE_CORREO_BASE):
            correos_de_prueba(base)

    @pytest.mark.parametrize("base", [None, "equipo@correo.test"])
    def test_los_ocho_correos_son_distintos(self, base):
        correos = list(correos_de_prueba(base).values())
        assert len(correos) == len(CUENTAS_PRUEBA) == 8
        assert len({c.lower() for c in correos}) == 8


class TestContrasena:
    def test_se_usa_la_variable_de_entorno(self):
        valor = secrets.token_urlsafe(16)  # nunca un literal en el código
        assert exigir_contrasena_de_prueba(valor) == valor

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
