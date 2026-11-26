from django.apps import AppConfig


class ComerciosConfig(AppConfig):
    name = "apps.comercios"
    label = "comercios"
    verbose_name = "Módulo comercial (perfiles, precios oficiales, promociones)"

    def ready(self):
        # DP-1 opción B (ADR-012): el módulo comercial se registra en el puerto de la comparación.
        # La comparación consulta el registro de core y nunca importa este módulo.
        from apps.comparacion.domain.extensiones import PUNTO_DATOS_COMERCIALES
        from core.extensiones import registrar

        from .selectors import EXTENSION

        registrar(PUNTO_DATOS_COMERCIALES, EXTENSION)
