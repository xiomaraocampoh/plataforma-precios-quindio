"""Huella de dispositivo para avisar de un ingreso nuevo. Nunca guarda la IP completa (Ley 1581)."""

import pytest

from apps.cuentas.domain.dispositivos import describir_navegador, huella_dispositivo, truncar_ip

pytestmark = pytest.mark.unit

CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "Version/18.0 Mobile Safari/604.1"
)


@pytest.mark.parametrize(
    ("ip", "esperado"),
    [
        ("203.0.113.57", "203.0.113.0/24"),
        ("2001:db8:abcd:12::1", "2001:db8:abcd::/48"),
        ("no-es-ip", ""),
        ("", ""),
    ],
)
def test_la_ip_se_trunca(ip, esperado):
    assert truncar_ip(ip) == esperado


def test_la_huella_no_contiene_la_ip_y_es_estable_en_la_misma_red():
    a = huella_dispositivo(user_agent=CHROME, ip="203.0.113.57", clave="k")
    assert "203.0.113" not in a and len(a) == 64
    assert a == huella_dispositivo(user_agent=CHROME, ip="203.0.113.200", clave="k")
    assert a != huella_dispositivo(user_agent=CHROME, ip="198.51.100.1", clave="k")
    assert a != huella_dispositivo(user_agent=IPHONE, ip="203.0.113.57", clave="k")


@pytest.mark.parametrize(
    ("agente", "esperado"),
    [
        (CHROME, "Chrome en Windows"),
        (IPHONE, "Safari en iPhone"),
        ("", "Navegador desconocido"),
    ],
)
def test_describe_el_navegador_sin_datos_personales(agente, esperado):
    assert describir_navegador(agente) == esperado
