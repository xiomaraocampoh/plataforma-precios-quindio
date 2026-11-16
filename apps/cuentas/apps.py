from django.apps import AppConfig


class CuentasConfig(AppConfig):
    name = "apps.cuentas"
    label = "cuentas"
    verbose_name = "Cuentas y roles"

    def ready(self):
        from . import signals  # noqa: F401  registra la sincronización rol → grupo
