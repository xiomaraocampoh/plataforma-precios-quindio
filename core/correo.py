"""Qué backend de correo usar según el entorno (ADR-021). Python puro: lo usa settings.

Render gratuito bloquea los puertos SMTP (25, 465 y 587), así que en producción el correo sale
por la API HTTPS de Brevo (puerto 443) con django-anymail. SMTP queda como opción local.
"""

ANYMAIL_BREVO = "anymail.backends.brevo.EmailBackend"
SMTP = "django.core.mail.backends.smtp.EmailBackend"
CONSOLA = "django.core.mail.backends.console.EmailBackend"


def elegir_backend_correo(*, brevo_api_key: str, email_host: str, explicito: str = "") -> str:
    """1) Con BREVO_API_KEY, la API de Brevo (gana incluso a un EMAIL_BACKEND=smtp heredado).
    2) Si no, el EMAIL_BACKEND explícito; SMTP solo si hay EMAIL_HOST. 3) Si no, la consola."""
    if (brevo_api_key or "").strip():
        return ANYMAIL_BREVO
    backend = (explicito or "").strip() or (SMTP if (email_host or "").strip() else CONSOLA)
    if backend == SMTP and not (email_host or "").strip():
        return CONSOLA  # sin servidor no hay a dónde enviar
    return backend


def describir_backend(backend: str) -> str:
    """Nombre legible para el diagnóstico (nunca incluye credenciales)."""
    return {
        ANYMAIL_BREVO: "API HTTPS de Brevo (django-anymail)",
        SMTP: "SMTP",
        CONSOLA: "consola (no se envía nada)",
    }.get(backend, backend)
