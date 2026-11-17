"""Pantallas de ingreso y registro: errores a la vista, campos marcados y ayudas visibles."""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

REGISTRO_CON_ERRORES = {
    "username": "ab c",
    "email": "",
    "password1": "12345678",
    "password2": "otra-distinta",
}


def _registro_con_errores(client) -> str:
    return client.post(reverse("cuentas:registro"), REGISTRO_CON_ERRORES).content.decode()


def _abrir(client, ruta: str) -> str:
    return client.get(reverse(ruta)).content.decode()


# ───────────── Resumen de errores y campos marcados ─────────────


def test_el_registro_con_errores_muestra_un_resumen_arriba_con_enlaces_a_cada_campo(client):
    html = _registro_con_errores(client)
    assert 'id="resumen-errores"' in html
    for campo in ("id_username", "id_password1", "id_password2", "id_acepto_tratamiento_datos"):
        assert f'href="#{campo}"' in html
    assert html.index('id="resumen-errores"') < html.index(
        'id="id_username"'
    )  # antes de los campos


def test_el_resumen_solo_aparece_si_hay_errores(client):
    assert "resumen-errores" not in _abrir(client, "cuentas:registro")
    assert "resumen-errores" not in _abrir(client, "cuentas:ingresar")


def test_un_solo_aviso_para_lectores_de_pantalla(client):
    # El resumen se anuncia; los mismos errores junto a cada campo no se repiten como alerta.
    assert _registro_con_errores(client).count('role="alert"') == 1


def test_los_campos_con_error_quedan_marcados_y_enlazados_a_su_mensaje(client):
    html = _registro_con_errores(client)
    assert 'aria-invalid="true"' in html
    assert 'id="id_username_error"' in html


def test_no_se_devuelven_las_contrasenas_escritas(client):
    html = _registro_con_errores(client)
    assert "12345678" not in html and "otra-distinta" not in html
    assert 'value="ab c"' in html  # el usuario sí se conserva para corregirlo


# ───────────── Ayudas en el registro ─────────────


def test_las_etiquetas_no_llevan_dos_puntos_y_las_ayudas_son_visibles(client):
    html = _abrir(client, "cuentas:registro")
    assert "Nombre de usuario:" not in html
    assert "3 a 30 caracteres" in html  # la regla se ve antes de equivocarse


def test_el_registro_muestra_las_reglas_de_la_clave(client):
    html = _abrir(client, "cuentas:registro")
    for regla in ("largo", "no-numerica", "coinciden"):
        assert f'data-regla="{regla}"' in html


@pytest.mark.parametrize(
    ("ruta", "campos"),
    [
        ("cuentas:registro", ["id_password1", "id_password2"]),
        ("cuentas:ingresar", ["id_password"]),
    ],
)
def test_las_contrasenas_se_pueden_mostrar(client, ruta, campos):
    html = _abrir(client, ruta)
    for campo in campos:
        assert f'aria-controls="{campo}"' in html
    assert html.count("data-ver-clave") == len(campos)


def test_el_envio_evita_el_doble_clic_y_avisa_que_esta_trabajando(client):
    registro = _abrir(client, "cuentas:registro")
    assert "data-una-vez" in registro and 'data-enviando="Creando cuenta…"' in registro
    ingreso = _abrir(client, "cuentas:ingresar")
    assert "data-una-vez" in ingreso and 'data-enviando="Ingresando…"' in ingreso


@pytest.mark.parametrize("ruta", ["cuentas:registro", "cuentas:ingresar"])
def test_las_pantallas_cargan_su_script(client, ruta):
    assert "js/cuentas" in _abrir(client, ruta)


# ───────────── Ingreso ─────────────


def test_ingreso_con_campos_vacios_dice_cual_falta_y_lo_resume(client):
    html = client.post(
        reverse("cuentas:ingresar"), {"username": "", "password": ""}
    ).content.decode()
    assert "Escribe tu nombre de usuario." in html
    assert "Escribe tu contraseña." in html
    assert 'id="resumen-errores"' in html
    assert 'href="#id_username"' in html and 'href="#id_password"' in html


def test_con_credenciales_incorrectas_el_resumen_ofrece_recuperar_la_clave(client, reportante):
    html = client.post(
        reverse("cuentas:ingresar"), {"username": "reportante1", "password": "incorrecta"}
    ).content.decode()
    resumen = html[html.index('id="resumen-errores"') :]
    assert reverse("cuentas:recuperar") in resumen[: resumen.index("</div>")]


def test_olvide_mi_contrasena_esta_junto_al_campo_y_antes_del_boton(client):
    html = _abrir(client, "cuentas:ingresar")
    enlace = html.index("¿Olvidaste tu contraseña?")
    assert html.index('id="id_password"') < enlace < html.index('type="submit"')
