from django import template

register = template.Library()


@register.filter
def esta_activo(objeto) -> bool:
    """Marca y categoría usan «activa»; producto y establecimiento, «activo»."""
    return bool(getattr(objeto, "activa", getattr(objeto, "activo", True)))
