"""Muestra el texto de K-nasta: escapa todo y solo permite **negrita** y saltos de línea."""

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from apps.canasta.domain.guia import tema_por_id

register = template.Library()
_NEGRITA = re.compile(r"\*\*(.+?)\*\*")


@register.filter
def texto_chat(texto: str):
    """Seguro frente a HTML: primero se escapa, después se convierte **x** en <strong>x</strong>."""
    seguro = escape(texto or "")
    seguro = _NEGRITA.sub(r"<strong>\1</strong>", seguro)
    return mark_safe(seguro.replace("\n", "<br>"))  # noqa: S308 (ya escapado arriba)


@register.filter
def tema_guia(id_tema: str):
    """El tema de la guía con ese id (para dibujar su paso a paso)."""
    return tema_por_id(id_tema)
