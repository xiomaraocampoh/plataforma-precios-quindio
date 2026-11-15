"""Verificación de salud para el monitor de disponibilidad (M-21, RNF-05).

Consolidado secc. 18.1: el endpoint comprueba la conexión a PostgreSQL y a la caché (Redis).
"""

import pytest
from django.urls import reverse

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_healthz_ok_cuando_bd_y_cache_responden(client):
    respuesta = client.get(reverse("healthz"))
    assert respuesta.status_code == 200
    assert respuesta.json() == {"estado": "ok", "bd": "ok", "cache": "ok"}


def test_healthz_503_si_la_cache_no_responde(client, monkeypatch):
    def caida(*args, **kwargs):
        raise ConnectionError("redis caído")

    monkeypatch.setattr("core.views.cache.set", caida)
    respuesta = client.get(reverse("healthz"))
    assert respuesta.status_code == 503
    assert respuesta.json()["cache"] == "error"
