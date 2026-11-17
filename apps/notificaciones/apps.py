import logging

from django.apps import AppConfig
from django.conf import settings

log = logging.getLogger("ahorrapues.correo")


class NotificacionesConfig(AppConfig):
    name = "apps.notificaciones"
    label = "notificaciones"
    verbose_name = "Notificaciones por correo"

    def ready(self):
        # En producción los enlaces de los correos salen de SITIO_URL: con localhost no sirven
        if not settings.DEBUG and "localhost" in settings.SITIO_URL:
            log.warning(
                "SITIO_URL apunta a localhost (%s): los enlaces de los correos no funcionarán. "
                "Defínala con la dirección pública, p. ej. https://tu-app.onrender.com",
                settings.SITIO_URL,
            )
