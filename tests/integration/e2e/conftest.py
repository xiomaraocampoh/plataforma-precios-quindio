"""Pruebas de navegador (Playwright + live_server). Requieren: playwright install chromium"""

import os

import pytest

pytest.importorskip("playwright", reason="instala requirements/dev.txt para las pruebas e2e")

# Playwright síncrono corre un bucle asyncio en el hilo de la prueba; las consultas del ORM que
# hace la prueba para verificar la BD son seguras porque el servidor vive en otro hilo.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")


@pytest.fixture
def pagina_con_sesion(live_server, context, client, reportante, arroz, tiendas):
    """Página de Playwright con la sesión del reportante ya iniciada."""
    client.force_login(reportante)
    context.add_cookies(
        [{"name": "sessionid", "value": client.cookies["sessionid"].value, "url": live_server.url}]
    )
    pagina = context.new_page()
    pagina.set_default_timeout(10_000)
    return pagina
