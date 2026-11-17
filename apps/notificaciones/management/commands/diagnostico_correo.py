"""Diagnóstico del correo en producción, sin mostrar secretos (ADR-021).

Uso:
    python manage.py diagnostico_correo
    python manage.py diagnostico_correo --enviar persona@ejemplo.com   # manda un correo de prueba

Muestra el backend activo, si hay BREVO_API_KEY o EMAIL_HOST (solo «sí/no»), SITIO_URL,
DEFAULT_FROM_EMAIL, la cola por estado y el último error. Nunca imprime claves.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.notificaciones import services
from core.correo import ANYMAIL_BREVO, SMTP, describir_backend


def _si_no(valor) -> str:
    return "sí" if valor else "no"


class Command(BaseCommand):
    help = "Muestra cómo está configurado el correo y el estado de la cola (sin secretos)."

    def add_arguments(self, parser):
        parser.add_argument("--enviar", metavar="CORREO", help="Envía un correo de prueba.")

    def handle(self, *args, enviar=None, **opciones):
        backend = settings.EMAIL_BACKEND
        self.stdout.write(f"Backend: {describir_backend(backend)}")
        self.stdout.write(
            f"BREVO_API_KEY definida: {_si_no(getattr(settings, 'BREVO_API_KEY', ''))}"
        )
        self.stdout.write(f"EMAIL_HOST definido: {_si_no(settings.EMAIL_HOST)}")
        self.stdout.write(f"SITIO_URL: {settings.SITIO_URL}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        self.stdout.write(f"CORREO_CRON_TOKEN definido: {_si_no(settings.CORREO_CRON_TOKEN)}")
        self._avisos(backend)
        cola = services.resumen_cola()
        texto = " · ".join(f"{estado}: {n}" for estado, n in cola["por_estado"].items())
        self.stdout.write(f"Cola: {texto}")
        self.stdout.write(f"Último error: {cola['ultimo_error'] or 'ninguno'}")
        if enviar:
            self._enviar(enviar)

    def _avisos(self, backend: str) -> None:
        if backend == SMTP and not settings.DEBUG:
            self.stdout.write(
                self.style.WARNING(
                    "SMTP en producción: Render gratuito bloquea los puertos 25, 465 y 587. "
                    "Defina BREVO_API_KEY para enviar por la API HTTPS."
                )
            )
        if backend not in (ANYMAIL_BREVO, SMTP):
            self.stdout.write(self.style.WARNING("Los correos no salen: se imprimen o se guardan."))
        if not settings.DEBUG and "localhost" in settings.SITIO_URL:
            self.stdout.write(self.style.WARNING("SITIO_URL apunta a localhost."))

    def _enviar(self, destinatario: str) -> None:
        error = services.enviar_prueba(destinatario)
        if error:
            raise CommandError(f"El correo de prueba no salió: {error}")
        self.stdout.write(self.style.SUCCESS("Correo de prueba enviado. Revise también el spam."))
