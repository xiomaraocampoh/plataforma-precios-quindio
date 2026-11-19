"""Filtro de plantilla: ícono de una categoría (la regla vive en el dominio, sin Django)."""

from django import template

from apps.catalogo.domain.iconos import icono_de_categoria

register = template.Library()


@register.filter
def icono_categoria(categoria) -> str:
    """Id del ícono del sprite para una categoría (o su nombre); genérico si no se reconoce."""
    return icono_de_categoria(getattr(categoria, "nombre", categoria))
