"""Lecturas de referencias externas (RF-07)."""

from datetime import timedelta

from django.utils import timezone

from .models import PrecioReferencia

DIAS_REFERENCIA = 30  # una referencia más vieja ya no orienta al consumidor


def referencia_sipsa(producto_id: int) -> PrecioReferencia | None:
    desde = timezone.localdate() - timedelta(days=DIAS_REFERENCIA)
    return (
        PrecioReferencia.objects.filter(
            producto_id=producto_id, fuente=PrecioReferencia.Fuente.SIPSA, fecha__gte=desde
        )
        .order_by("-fecha", "precio_por_kg")
        .first()
    )
