"""Filtros de presentación del tiempo transcurrido."""

from django import template
from django.utils.timesince import timesince

register = template.Library()


@register.filter
def hace(valor, ahora=None) -> str:
    """«19 horas» en vez de «19 horas, 50 minutos»: una sola unidad, más fácil de leer."""
    texto = timesince(valor, ahora, depth=1)
    return "instantes" if texto.startswith("0") else texto
