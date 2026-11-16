"""Consultas del lado lectura (Consumidores). Capa de aplicación — solo lectura.

Separación lectura/escritura "CQRS ligero": misma BD, caminos de código distintos.
Si la prueba de carga (EC-04) no alcanza p95 ≤ 2 s, el siguiente paso es una vista
materializada / tabla de lectura alimentada por los servicios de escritura (ver ADR-0002).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from apps.catalogo import selectors as catalogo
from apps.catalogo.domain.normalizacion import precio_por_unidad
from apps.catalogo.models import Producto
from apps.establecimientos.models import Establecimiento
from apps.moderacion.selectors import denunciados_por
from apps.precios.domain.confianza import nivel_confianza
from apps.precios.domain.vigencia import Fuente, es_vigente, fecha_de_referencia
from apps.precios.models import ReportePrecio
from apps.precios.selectors import (
    confirmaciones_por_reporte,
    confirmados_hoy,
    politica_vigencia,
    reportes_propios,
)
from core.cache import clave_comparacion, clave_resumen, ttl_comparacion

from .domain.filtros import FiltroUbicacion, filtrar
from .domain.ranking import ResultadoComparacion, ordenar_neutral
from .domain.resumen import ResumenComparacion, resumir_precios


def buscar_productos(texto: str, limite: int = 10):
    """RF-04: la búsqueda vive en el catálogo; aquí solo se reexpone para las vistas."""
    return catalogo.buscar_productos(texto, limite)


@dataclass(frozen=True)
class FilaComparacion:
    """Un resultado de la comparación y los datos que la interfaz necesita a su lado.

    El orden lo fija SOLO `ordenar_neutral` sobre los `ResultadoComparacion` (EC-06); estos datos
    extra (reporte, ubicación, última confirmación) nunca entran en la clave de orden.
    """

    resultado: ResultadoComparacion
    reporte_id: int
    municipio: str
    barrio: str
    ultima_confirmacion: datetime | None


def _reportes_candidatos(producto_id: int, desde: datetime):
    # Un reporte viejo confirmado hace poco con «Sigue igual» sigue siendo candidato (RF-14)
    return (
        ReportePrecio.objects.filter(
            Q(fecha_observacion__gte=desde) | Q(confirmaciones__creado_en__gte=desde),
            presentacion__producto_id=producto_id,
            estado=ReportePrecio.Estado.PUBLICADO,
            establecimiento__activo=True,
        )
        .select_related("presentacion__producto__categoria", "establecimiento")
        .order_by("establecimiento_id", "presentacion_id", "-fecha_observacion")
        .distinct()
    )


def _calcular_filas(producto_id: int) -> list[FilaComparacion]:
    ahora = timezone.now()
    politica = politica_vigencia()
    desde = ahora - timedelta(days=max(politica.dias_reporte, politica.dias_oficial))

    ultimos: dict[tuple[int, int], ReportePrecio] = {}
    iguales: dict[tuple[int, int], int] = {}
    for r in _reportes_candidatos(producto_id, desde):  # un solo query; agrupación en memoria
        clave = (r.establecimiento_id, r.presentacion_id)
        if clave not in ultimos:
            ultimos[clave] = r
            iguales[clave] = 0
        elif r.precio == ultimos[clave].precio:
            iguales[clave] += 1
    confirmaciones = confirmaciones_por_reporte([r.pk for r in ultimos.values()])

    extras: dict[ResultadoComparacion, tuple] = {}
    for clave, r in ultimos.items():
        n_conf, ultima = confirmaciones.get(r.pk, (0, None))
        referencia = fecha_de_referencia(r.fecha_observacion, [ultima] if ultima else [])
        perecedero = r.presentacion.producto.categoria.perecedera
        if not es_vigente(
            min(referencia, ahora),
            ahora,
            Fuente(r.fuente),
            perecedero=perecedero,
            politica=politica,
        ):
            continue
        unitario, base = precio_por_unidad(r.precio, r.presentacion.cantidad, r.presentacion.unidad)
        resultado = ResultadoComparacion(
            establecimiento_id=r.establecimiento_id,
            establecimiento=r.establecimiento.nombre,
            presentacion=str(r.presentacion),
            precio=r.precio,
            precio_unitario=unitario,
            unidad_base=base.value,
            fuente=r.fuente,
            confianza=nivel_confianza(Fuente(r.fuente), iguales[clave] + n_conf, False).value,
            fecha_observacion=r.fecha_observacion,
        )
        extras[resultado] = (r.pk, r.establecimiento.municipio, r.establecimiento.barrio, ultima)
    return [FilaComparacion(r, *extras[r]) for r in ordenar_neutral(list(extras))]


def comparar_filas(producto_id: int) -> list[FilaComparacion]:
    """Cache-aside: TTL corto (D-01 ≤ 1 min) + invalidación al registrar o confirmar."""
    return cache.get_or_set(
        clave_comparacion(producto_id),
        lambda: _calcular_filas(producto_id),
        ttl_comparacion(),
    )


def comparar_producto(producto_id: int) -> list[ResultadoComparacion]:
    """Contrato de la API pública: solo los resultados, en orden neutral."""
    return [f.resultado for f in comparar_filas(producto_id)]


def comparar_con_resumen(
    producto_id: int, filtro: FiltroUbicacion | None = None
) -> tuple[list[FilaComparacion], ResumenComparacion]:
    """RF-19: el filtro de ubicación solo reduce las filas ya ordenadas (EC-06)."""
    filas = comparar_filas(producto_id)
    if filtro is not None and filtro.activo:
        filas = filtrar(filas, filtro, lambda f: (f.municipio, f.barrio))
    return filas, resumir_precios([f.resultado for f in filas])


def ubicaciones_de(filas: list[FilaComparacion]) -> dict[str, list[str]]:
    """Opciones de los filtros: solo municipios y barrios que tienen precio vigente."""
    return {
        "municipios": sorted({f.municipio for f in filas if f.municipio}),
        "barrios": sorted({f.barrio for f in filas if f.barrio}),
    }


def _calcular_resumen_plataforma() -> dict[str, int]:
    return {
        "productos": Producto.objects.count(),
        "establecimientos": Establecimiento.objects.filter(activo=True).count(),
        "reportes": ReportePrecio.objects.filter(estado=ReportePrecio.Estado.PUBLICADO).count(),
    }


def resumen_plataforma() -> dict[str, int]:
    """Cifras de la portada. Se invalida junto con la comparación al registrar un precio."""
    return cache.get_or_set(clave_resumen(), _calcular_resumen_plataforma, ttl_comparacion())


def productos_destacados(limite: int = 8):
    """Productos con más reportes publicados (un solo query; sin criterio comercial)."""
    return list(
        Producto.objects.select_related("categoria")
        .annotate(
            n_reportes=Count(
                "presentaciones__reportes",
                filter=Q(presentaciones__reportes__estado=ReportePrecio.Estado.PUBLICADO),
            )
        )
        .filter(n_reportes__gt=0)
        .order_by("-n_reportes", "nombre")[:limite]
    )


def ejemplo_comparacion(producto_id: int, limite: int = 4) -> list[dict]:
    """Filas para el gráfico de barras de la portada (precio por unidad, orden neutral)."""
    filas = comparar_producto(producto_id)[:limite]
    if len(filas) < 2 or len({f.unidad_base for f in filas}) != 1:
        return []
    maximo = max(f.precio_unitario for f in filas)
    return [
        {
            "establecimiento": f.establecimiento,
            "presentacion": f.presentacion,
            "precio_unitario": f.precio_unitario,
            "unidad_base": f.unidad_base,
            "porcentaje": int(f.precio_unitario / maximo * 100) if maximo else 0,
        }
        for f in filas
    ]


def estado_del_usuario(usuario, reporte_ids: list[int]) -> dict[str, set[int]]:
    """Qué botones mostrar a quien consulta. No se cachea: depende de la persona."""
    if not usuario.is_authenticated:
        return {"confirmados_hoy": set(), "propios": set(), "denunciados": set()}
    return {
        "confirmados_hoy": confirmados_hoy(usuario, reporte_ids),
        "propios": reportes_propios(usuario, reporte_ids),
        "denunciados": denunciados_por(usuario, reporte_ids),
    }
