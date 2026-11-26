"""Importación de precios de referencia SIPSA (RF-07). Capa de aplicación."""

import hashlib
import logging
from dataclasses import dataclass, field
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from apps.catalogo import selectors as catalogo
from apps.catalogo import services as catalogo_servicios

from .clients.asistente import (  # noqa: F401  (se reexporta para K-nasta)
    AsistenteClaude,
    AsistenteNoDisponibleError,
    ModeloConversacional,
    RespuestaModelo,
    bloque_imagen,
)
from .clients.sipsa import PrecioExterno
from .clients.vision import (  # noqa: F401  (se reexporta para las vistas)
    ReconocedorClaude,
    ReconocedorDeProductos,
    ReconocimientoNoDisponibleError,
)
from .domain.escaneo import ControlDeEnvio, ResultadoEscaneo
from .domain.reconocimiento import PistaProducto, tipo_de_imagen
from .models import PrecioReferencia

logger = logging.getLogger(__name__)


@dataclass
class ResumenImportacion:
    creados: int = 0
    actualizados: int = 0
    sin_producto: list[str] = field(default_factory=list)
    productos_creados: list[str] = field(default_factory=list)


CATEGORIA_FRESCOS = "Frutas y verduras"


def _crear_fresco(nombre: str):
    """--crear-faltantes: un producto fresco sin marca, con presentación de 1 kg (por servicios
    del catálogo, con su regla de duplicados D-05). None si se parece a uno existente."""
    categoria, _ = catalogo_servicios.asegurar_categoria(nombre=CATEGORIA_FRESCOS, perecedera=True)
    try:
        producto, _ = catalogo_servicios.asegurar_producto(
            nombre=nombre, marca=None, categoria=categoria
        )
    except catalogo_servicios.PosibleDuplicadoError:
        return None
    catalogo_servicios.asegurar_presentacion(producto=producto, cantidad=Decimal(1), unidad="kg")
    return producto


@transaction.atomic
def importar_referencias(
    precios: list[PrecioExterno], *, crear_faltantes: bool = False
) -> ResumenImportacion:
    """Asocia cada fila a un producto del catálogo y la guarda con fuente «sipsa».

    Idempotente: reimportar actualiza (producto, mercado, fecha) sin duplicar.
    Las filas cuyo producto no está en el catálogo se informan y no se guardan, salvo con
    `crear_faltantes`, que crea el producto fresco (sin marca, 1 kg).
    """
    resumen = ResumenImportacion()
    for p in precios:
        producto = catalogo.producto_por_nombre(p.producto)
        if producto is None and crear_faltantes:
            producto = _crear_fresco(p.producto)
            if producto is not None:
                resumen.productos_creados.append(p.producto)
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


def _contar(clave: str, segundos: int) -> int:
    cache.add(clave, 0, timeout=segundos)
    return cache.incr(clave)


def _identidad(usuario, ip: str) -> tuple[str, int]:
    """Quién consume el cupo y cuánto le toca. De los visitantes solo se guarda una huella
    de la dirección (no la dirección), y tienen un tope menor que quien tiene cuenta."""
    cfg = settings.INTEGRACIONES
    if usuario is not None and getattr(usuario, "is_authenticated", False):
        return f"u{usuario.pk}", cfg["RECONOCIMIENTOS_POR_HORA"]
    huella = hashlib.sha256(f"{settings.SECRET_KEY}|{ip}".encode()).hexdigest()[:16]
    return f"a{huella}", cfg["RECONOCIMIENTOS_ANONIMO_POR_HORA"]


def _exigir_cupo_de_reconocimiento(usuario, ip: str) -> None:
    ahora = timezone.now()
    quien, limite = _identidad(usuario, ip)
    if (
        _contar(f"reconocimiento:v1:dia:{ahora:%Y%m%d}", 86400)
        > settings.INTEGRACIONES["RECONOCIMIENTOS_POR_DIA_TOTAL"]
    ):
        raise LimiteDeReconocimientosExcedidoError(
            "La búsqueda por foto alcanzó su límite de hoy. "
            "Puedes buscar por nombre o escanear el código de barras."
        )
    if _contar(f"reconocimiento:v1:{quien}:{ahora:%Y%m%d%H}", 3600) > limite:
        raise LimiteDeReconocimientosExcedidoError(
            f"Alcanzaste el límite de {limite} búsquedas por foto por hora. "
            "Mientras tanto puedes buscar por nombre o escanear el código."
        )


def reconocer_producto(*, usuario, imagen: bytes, ip: str = "") -> PistaProducto | None:
    """Identifica un producto en una foto. La imagen no se guarda: solo vive en memoria.

    Puede usarla un visitante sin cuenta (más fácil), con topes por persona y diario total
    para acotar el gasto en la API externa."""
    tipo = tipo_de_imagen(imagen)  # una imagen inválida no consume cupo ni llega a la IA
    _exigir_cupo_de_reconocimiento(usuario, ip)
    return _crear_reconocedor().reconocer(imagen, tipo)


class LimiteDelAsistenteExcedidoError(Exception):
    """Cada mensaje a K-nasta con IA cuesta dinero: topes por hora y por día."""


def crear_asistente() -> ModeloConversacional:
    return AsistenteClaude()


def exigir_cupo_del_asistente(usuario, ip: str) -> None:
    """Un cupo por mensaje de la persona (no por cada vuelta de herramientas)."""
    cfg = settings.INTEGRACIONES
    ahora = timezone.now()
    quien, _ = _identidad(usuario, ip)
    limite = (
        cfg["ASISTENTE_MENSAJES_POR_HORA"]
        if quien.startswith("u")
        else cfg["ASISTENTE_ANONIMO_POR_HORA"]
    )
    if _contar(f"asistente:v1:dia:{ahora:%Y%m%d}", 86400) > cfg["ASISTENTE_POR_DIA_TOTAL"]:
        raise LimiteDelAsistenteExcedidoError("K-nasta alcanzó su límite de IA de hoy.")
    if _contar(f"asistente:v1:{quien}:{ahora:%Y%m%d%H}", 3600) > limite:
        raise LimiteDelAsistenteExcedidoError(
            f"Alcanzaste el límite de {limite} mensajes por hora."
        )


def asistente_ia_activo() -> bool:
    """K-nasta usa la IA (ADR-0030) solo con el interruptor y la clave.

    Sin ellos funciona con reglas y no se anuncia como IA: la etiqueta «IA» nunca promete algo que
    no está ocurriendo.
    """
    return reconocimiento_activo() and bool(settings.INTEGRACIONES["ASISTENTE_IA_ACTIVO"])


def escaneo_vivo_activo() -> bool:
    """El escáner en vivo (ADR-0026) exige el interruptor y la clave; sin ellos queda la foto o el
    código de barras, que se lee en el teléfono."""
    return reconocimiento_activo() and bool(settings.INTEGRACIONES["ESCANEO_VIVO_ACTIVO"])


def control_de_envio() -> ControlDeEnvio:
    """Los parámetros que el navegador usa para decidir cuándo enviar un fotograma."""
    cfg = settings.INTEGRACIONES
    return ControlDeEnvio(
        intervalo_ms=cfg["ESCANEO_INTERVALO_MS"],
        max_por_sesion=cfg["ESCANEO_MAX_FOTOGRAMAS_SESION"],
    )


def escanear_fotograma(*, usuario, imagen: bytes, ip: str = "") -> ResultadoEscaneo:
    """Qué hay en un fotograma del escáner en vivo: un empaque, una etiqueta de precio o nada.

    Consume el mismo cupo por hora y por día que la foto manual. La imagen vive solo en memoria:
    no se guarda en disco, en la base de datos ni en los registros; del resultado solo se anota
    el tipo y la confianza, sin nada de la persona (M-15)."""
    tipo = tipo_de_imagen(imagen)
    _exigir_cupo_de_reconocimiento(usuario, ip)
    resultado = _crear_reconocedor().escanear(imagen, tipo)
    leido = resultado.etiqueta or resultado.pista
    confianza = leido.confianza if leido else "-"
    logger.info("Escaneo en vivo: %s (confianza %s)", resultado.tipo.value, confianza)
    return resultado
