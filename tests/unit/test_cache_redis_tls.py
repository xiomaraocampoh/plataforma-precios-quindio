"""La caché de producción acepta Redis con TLS («rediss://»), como el de Upstash (ADR-0031).

No abre ninguna conexión: solo comprueba que el cliente de Django arma un pool con SSL.
"""

import pytest
import redis
from django.core.cache.backends.redis import RedisCache

pytestmark = pytest.mark.unit


def _pool(url: str) -> redis.ConnectionPool:
    return RedisCache(url, {})._cache._get_connection_pool(write=True)


def test_rediss_usa_conexion_tls_y_verifica_el_certificado():
    pool = _pool("rediss://default:clave@ejemplo.upstash.io:6379")
    assert pool.connection_class is redis.SSLConnection
    assert pool.connection_kwargs["host"] == "ejemplo.upstash.io"
    assert pool.connection_kwargs.get("ssl_cert_reqs", "required") == "required"


def test_redis_sin_tls_sigue_funcionando_para_render_y_docker():
    assert _pool("redis://localhost:6379/0").connection_class is redis.Connection
