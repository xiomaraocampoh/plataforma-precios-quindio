from django.db import connection
from django.http import JsonResponse


def healthz(request):
    """Health check para el monitor de disponibilidad (M-21)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        estado, codigo = "ok", 200
    except Exception:  # noqa: BLE001 — el health check nunca debe propagar
        estado, codigo = "db_error", 503
    return JsonResponse({"estado": estado}, status=codigo)
