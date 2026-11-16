"""Configuración común de pytest.

`client.force_login(usuario)` simula un ingreso COMPLETO, incluido el segundo factor (RF-27): sin
esto, el middleware cerraría la sesión de cada moderador o administrador de las pruebas. Las
pruebas del middleware arman a propósito sesiones sin esa marca (ver tests/integration/cuentas).
"""

from django.test.client import ClientMixin

from apps.cuentas.views.ingreso import FLAG

_login_original = ClientMixin._login


def _login_con_segundo_factor(self, user, backend=None):
    _login_original(self, user, backend)
    sesion = self.session
    sesion[FLAG] = "verificado"
    sesion.save()


ClientMixin._login = _login_con_segundo_factor
