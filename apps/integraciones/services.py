"""Importación de precios de referencia SIPSA (RF-07). Capa de aplicación."""

from dataclasses import dataclass, field

from django.db import transaction

from apps.catalogo import selectors as catalogo

from .clients.sipsa import PrecioExterno
from .models import PrecioReferencia


@dataclass
class ResumenImportacion:
    creados: int = 0
    actualizados: int = 0
    sin_producto: list[str] = field(default_factory=list)


@transaction.atomic
def importar_referencias(precios: list[PrecioExterno]) -> ResumenImportacion:
    """Asocia cada fila a un producto del catálogo y la guarda con fuente «sipsa».

    Idempotente: reimportar el archivo actualiza (producto, mercado, fecha) sin duplicar.
    Las filas cuyo producto no está en el catálogo se informan y no se guardan.
    """
    resumen = ResumenImportacion()
    for p in precios:
        producto = catalogo.producto_por_nombre(p.producto)
        if producto is None:
            resumen.sin_producto.append(p.producto)
            continue
        _, creado = PrecioReferencia.objects.update_or_create(
            producto=producto,
            mercado=p.mercado,
            fecha=p.fecha,
            fuente=PrecioReferencia.Fuente.SIPSA,
            defaults={"precio_por_kg": p.precio_por_kg},
        )
        if creado:
            resumen.creados += 1
        else:
            resumen.actualizados += 1
    return resumen
