"""Consultas del lado lectura (Consumidores). Capa de aplicación — solo lectura.

Separación lectura/escritura "CQRS ligero": misma BD, caminos de código distintos.
Si la prueba de carga (EC-04) no alcanza p95 ≤ 2 s, el siguiente paso es una vista
materializada / tabla de lectura alimentada por los servicios de escritura (ver ADR-0002).
"""

from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.catalogo.domain.normalizacion import precio_por_unidad
from apps.catalogo.models import Producto
from apps.precios.domain.confianza import nivel_confianza
from apps.precios.domain.vigencia import Fuente, PoliticaVigencia, es_vigente
from apps.precios.models import ReportePrecio
from core.cache import clave_comparacion, ttl_comparacion

from .domain.ranking import ResultadoComparacion, ordenar_neutral


def buscar_productos(texto: str, limite: int = 10):
    texto = (texto or "").strip()
    if len(texto) < 2:
        return Producto.objects.none()
    return Producto.objects.filter(nombre__icontains=texto).order_by("nombre")[:limite]


def _politica() -> PoliticaVigencia:
    p = settings.PRECIOS
    return PoliticaVigencia(
        dias_reporte=p["VIGENCIA_REPORTE_DIAS"],
        dias_perecedero=p["VIGENCIA_PERECEDERO_DIAS"],
        dias_oficial=p["VIGENCIA_OFICIAL_DIAS"],
    )


def _calcular_comparacion(producto_id: int) -> list[ResultadoComparacion]:
    ahora = timezone.now()
    politica = _politica()
    desde = ahora - timedelta(days=max(politica.dias_reporte, politica.dias_oficial))
    reportes = (
        ReportePrecio.objects.filter(
            presentacion__producto_id=producto_id,
            estado=ReportePrecio.Estado.PUBLICADO,
            fecha_observacion__gte=desde,
            establecimiento__activo=True,
        )
        .select_related("presentacion__producto__categoria", "establecimiento")
        .order_by("establecimiento_id", "presentacion_id", "-fecha_observacion")
    )

    ultimos: dict[tuple[int, int], ReportePrecio] = {}
    confirmaciones: dict[tuple[int, int], int] = {}
    for r in reportes:  # un solo query; agrupación en memoria
        clave = (r.establecimiento_id, r.presentacion_id)
        if clave not in ultimos:
            ultimos[clave] = r
            confirmaciones[clave] = 0
        elif r.precio == ultimos[clave].precio:
            confirmaciones[clave] += 1

    resultados = []
    for clave, r in ultimos.items():
        perecedero = r.presentacion.producto.categoria.perecedera
        if not es_vigente(
            r.fecha_observacion, ahora, Fuente(r.fuente), perecedero=perecedero, politica=politica
        ):
            continue
        unitario, base = precio_por_unidad(r.precio, r.presentacion.cantidad, r.presentacion.unidad)
        resultados.append(
            ResultadoComparacion(
                establecimiento_id=r.establecimiento_id,
                establecimiento=r.establecimiento.nombre,
                presentacion=str(r.presentacion),
                precio=r.precio,
                precio_unitario=unitario,
                unidad_base=base.value,
                fuente=r.fuente,
                confianza=nivel_confianza(Fuente(r.fuente), confirmaciones[clave], False).value,
                fecha_observacion=r.fecha_observacion,
            )
        )
    return ordenar_neutral(resultados)


def comparar_producto(producto_id: int) -> list[ResultadoComparacion]:
    """Cache-aside: TTL corto (D-01 ≤ 1 min) + invalidación al registrar."""
    return cache.get_or_set(
        clave_comparacion(producto_id),
        lambda: _calcular_comparacion(producto_id),
        ttl_comparacion(),
    )
