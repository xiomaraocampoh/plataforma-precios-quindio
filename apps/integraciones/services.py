"""Importación de precios de referencia SIPSA (RF-07). Capa de aplicación."""

from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.catalogo import selectors as catalogo

from .clients.sipsa import PrecioExterno
from .clients.vision import ReconocedorClaude, ReconocedorDeProductos
from .domain.reconocimiento import PistaProducto, tipo_de_imagen
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


class LimiteDeReconocimientosExcedidoError(Exception):
    """Cada reconocimiento por foto cuesta dinero: máximo por hora y por usuario (como RN-10)."""


def _crear_reconocedor() -> ReconocedorDeProductos:
    return ReconocedorClaude()


def reconocimiento_activo() -> bool:
    return bool(settings.INTEGRACIONES["ANTHROPIC_API_KEY"])


def _exigir_cupo_de_reconocimiento(usuario) -> None:
    limite = settings.INTEGRACIONES["RECONOCIMIENTOS_POR_HORA"]
    clave = f"reconocimiento:v1:{usuario.pk}:{timezone.now():%Y%m%d%H}"
    cache.add(clave, 0, timeout=3600)
    if cache.incr(clave) > limite:
        raise LimiteDeReconocimientosExcedidoError(
            f"Alcanzaste el límite de {limite} búsquedas por foto por hora. "
            "Mientras tanto puedes buscar por nombre o escanear el código."
        )


def reconocer_producto(*, usuario, imagen: bytes) -> PistaProducto | None:
    """Identifica un producto en una foto. La imagen no se guarda: solo vive en memoria."""
    tipo = tipo_de_imagen(imagen)  # una imagen inválida no consume cupo ni llega a la IA
    _exigir_cupo_de_reconocimiento(usuario)
    return _crear_reconocedor().reconocer(imagen, tipo)
