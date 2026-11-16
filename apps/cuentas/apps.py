from django.apps import AppConfig


class CuentasConfig(AppConfig):
    name = "apps.cuentas"
    label = "cuentas"
    verbose_name = "Cuentas y roles"

    def ready(self):
        from . import signals  # noqa: F401  registra la sincronización rol → grupo
        from .services import correo

        correo.registrar_en_notificaciones()  # enlaces firmados que se regeneran al reintentar
