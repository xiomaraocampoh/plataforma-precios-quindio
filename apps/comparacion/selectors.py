"""Consultas del lado lectura (Consumidores). Capa de aplicación — solo lectura.

Separación lectura/escritura "CQRS ligero": misma BD, caminos de código distintos.
Si la prueba de carga (EC-04) no alcanza p95 ≤ 2 s, el siguiente paso es una vista
materializada / tabla de lectura alimentada por los servicios de escritura (ver ADR-0002).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from apps.catalogo import selectors as catalogo
from apps.catalogo.domain.normalizacion import formatear_cantidad, precio_por_unidad
from apps.establecimientos.domain.mapas import enlace_mapa
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

from .domain.filtros import FiltroPrecio, FiltroUbicacion, filtrar, filtrar_por_precio
from .domain.ranking import ResultadoComparacion, ordenar_neutral
from .domain.resumen import ResumenComparacion, resumir_precios
from .domain.tarjeta import (
    AYUDA_POR_UNIDAD,
    antiguedad,
    etiqueta_fuente,
    formatear_pesos,
    texto_confianza,
    texto_por_unidad,
)

MIN_CARACTERES_BUSQUEDA = catalogo.MIN_CARACTERES_BUSQUEDA  # una sola fuente: el catálogo (RF-04)
MIN_FILAS_EJEMPLO = 2  # el gráfico de la portada necesita al menos dos precios que comparar


def buscar_productos(texto: str, limite: int = 10):
    """RF-04: la búsqueda vive en el catálogo; aquí solo se reexpone para las vistas."""
    return catalogo.buscar_productos(texto, limite)


@dataclass(frozen=True)
class FilaComparacion:
    """Un resultado de la comparación y los datos que la tarjeta necesita a su lado (RF-16).

    El orden lo fija SOLO `ordenar_neutral` sobre los `ResultadoComparacion` (EC-06); estos datos
    extra (producto, comercio, dirección, mapa, confirmación) nunca entran en la clave de orden.
    Del autor no hay nada: ni nombre, ni usuario, ni ubicación (M-15, EC-07).
    """

    resultado: ResultadoComparacion
    reporte_id: int
    municipio: str
    barrio: str
    ultima_confirmacion: datetime | None
    producto: str = ""
    marca: str = ""
    cantidad: Decimal = Decimal("0")
    unidad: str = ""
    tipo: str = ""
    direccion: str = ""
    enlace_mapa: str | None = None

    # ---- textos de la tarjeta (dominio puro; la plantilla solo los muestra) ----
    @property
    def presentacion_texto(self) -> str:
        return f"{formatear_cantidad(self.cantidad)} {self.unidad}" if self.unidad else ""

    @property
    def precio_texto(self) -> str:
        return formatear_pesos(self.resultado.precio)

    @property
    def por_unidad_texto(self) -> str:
        return texto_por_unidad(self.resultado.precio_unitario, self.resultado.unidad_base)

    @property
    def ayuda_por_unidad(self) -> str:
        return AYUDA_POR_UNIDAD

    @property
    def fuente_texto(self) -> str:
        return etiqueta_fuente(self.resultado.fuente)

    @property
    def confianza(self) -> tuple[str, str]:
        return texto_confianza(self.resultado.confianza)

    @property
    def antiguedad(self) -> str:  # se calcula al mostrar: la fila puede venir de la caché
        return antiguedad(self.resultado.fecha_observacion, timezone.now())


def _reportes_candidatos(producto_ids: list[int], desde: datetime):
    # Un reporte viejo confirmado hace poco con «Sigue igual» sigue siendo candidato (RF-14)
    return (
        ReportePrecio.objects.filter(
            Q(fecha_observacion__gte=desde) | Q(confirmaciones__creado_en__gte=desde),
            presentacion__producto_id__in=producto_ids,
            presentacion__activa=True,  # una presentación retirada del catálogo no se compara
            estado=ReportePrecio.Estado.PUBLICADO,
            establecimiento__activo=True,
        )
        .select_related(
            "presentacion__producto__categoria", "presentacion__producto__marca", "establecimiento"
        )
        .order_by("establecimiento_id", "presentacion_id", "-fecha_observacion")
        .distinct()
    )


def _ultimos_por_par(producto_ids: list[int], desde: datetime):
    """El reporte más reciente por (local, presentación) y cuántos anteriores dicen lo mismo."""
    ultimos: dict[tuple[int, int], ReportePrecio] = {}
    iguales: dict[tuple[int, int], int] = {}
    for r in _reportes_candidatos(producto_ids, desde):  # un solo query; agrupación en memoria
        clave = (r.establecimiento_id, r.presentacion_id)
        if clave not in ultimos:
            ultimos[clave] = r
            iguales[clave] = 0
        elif r.precio == ultimos[clave].precio:
            iguales[clave] += 1
    return ultimos, iguales


def _fila(r: ReportePrecio, resultado: ResultadoComparacion, ultima) -> FilaComparacion:
    local, presentacion = r.establecimiento, r.presentacion
    return FilaComparacion(
        resultado=resultado,
        reporte_id=r.pk,
        municipio=local.municipio,
        barrio=local.barrio,
        ultima_confirmacion=ultima,
        producto=presentacion.producto.nombre,
        marca=presentacion.producto.marca.nombre if presentacion.producto.marca else "",
        cantidad=presentacion.cantidad,
        unidad=presentacion.unidad,
        tipo=local.get_tipo_display(),
        direccion=local.direccion,
        enlace_mapa=enlace_mapa(
            local.latitud,
            local.longitud,
            direccion=local.direccion,
            barrio=local.barrio,
            municipio=local.municipio,
        ),
    )


def _resultado(r: ReportePrecio, n_iguales: int) -> ResultadoComparacion:
    unitario, base = precio_por_unidad(r.precio, r.presentacion.cantidad, r.presentacion.unidad)
    return ResultadoComparacion(
        establecimiento_id=r.establecimiento_id,
        establecimiento=r.establecimiento.nombre,
        presentacion=str(r.presentacion),
        precio=r.precio,
        precio_unitario=unitario,
        unidad_base=base.value,
        fuente=r.fuente,
        confianza=nivel_confianza(Fuente(r.fuente), n_iguales, False).value,
        fecha_observacion=r.fecha_observacion,
    )


def _calcular_filas_de(producto_ids: list[int]) -> dict[int, list[FilaComparacion]]:
    """Filas vigentes de varios productos con un número constante de queries (sin N+1)."""
    ahora = timezone.now()
    politica = politica_vigencia()
    desde = ahora - timedelta(days=max(politica.dias_reporte, politica.dias_oficial))
    ultimos, iguales = _ultimos_por_par(producto_ids, desde)
    confirmaciones = confirmaciones_por_reporte([r.pk for r in ultimos.values()])

    por_producto: dict[int, dict[ResultadoComparacion, FilaComparacion]] = {
        pid: {} for pid in producto_ids
    }
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
        resultado = _resultado(r, iguales[clave] + n_conf)
        por_producto[r.presentacion.producto_id][resultado] = _fila(r, resultado, ultima)
    return {
        pid: [filas[r] for r in ordenar_neutral(list(filas))]  # EC-06: solo el orden neutral
        for pid, filas in por_producto.items()
    }


def _calcular_filas(producto_id: int) -> list[FilaComparacion]:
    return _calcular_filas_de([producto_id])[producto_id]


def comparar_filas(producto_id: int) -> list[FilaComparacion]:
    """Cache-aside: TTL corto (D-01 ≤ 1 min) + invalidación al registrar o confirmar."""
    return cache.get_or_set(
        clave_comparacion(producto_id),
        lambda: _calcular_filas(producto_id),
        ttl_comparacion(),
    )


def primeras_filas(producto_ids: list[int]) -> dict[int, FilaComparacion | None]:
    """Listado de productos: la primera fila en el orden neutral de cada uno (o None).

    Usa la misma caché por producto que la comparación y calcula las que faltan en un solo lote.
    """
    claves = {clave_comparacion(pid): pid for pid in producto_ids}
    en_cache = cache.get_many(list(claves))
    faltan = [pid for clave, pid in claves.items() if clave not in en_cache]
    calculadas = _calcular_filas_de(faltan) if faltan else {}
    if calculadas:
        cache.set_many(
            {clave_comparacion(pid): filas for pid, filas in calculadas.items()},
            ttl_comparacion(),
        )
    todas = {pid: en_cache.get(clave, calculadas.get(pid)) for clave, pid in claves.items()}
    return {pid: (filas[0] if filas else None) for pid, filas in todas.items()}


def tarjetas_de_productos(productos) -> list[tuple]:
    """(producto, primera fila o None) para el listado, en el orden en que llegan (alfabético)."""
    productos = list(productos)
    primeras = primeras_filas([p.pk for p in productos])
    return [(p, primeras[p.pk]) for p in productos]


def comparar_producto(producto_id: int) -> list[ResultadoComparacion]:
    """Contrato de la API pública: solo los resultados, en orden neutral."""
    return [f.resultado for f in comparar_filas(producto_id)]


def comparar_con_resumen(
    producto_id: int,
    filtro: FiltroUbicacion | None = None,
    filtro_precio: FiltroPrecio | None = None,
) -> tuple[list[FilaComparacion], ResumenComparacion]:
    """RF-19: el filtro de ubicación solo reduce las filas ya ordenadas (EC-06)."""
    filas = comparar_filas(producto_id)
    if filtro is not None and filtro.activo:
        filas = filtrar(filas, filtro, lambda f: (f.municipio, f.barrio))
    if filtro_precio is not None and filtro_precio.activo:  # precio total, el que ve la persona
        filas = filtrar_por_precio(filas, filtro_precio, lambda f: f.resultado.precio)
    return filas, resumir_precios([f.resultado for f in filas])


def ubicaciones_de(filas: list[FilaComparacion]) -> dict[str, list[str]]:
    """Opciones de los filtros: solo municipios y barrios que tienen precio vigente."""
    return {
        "municipios": sorted({f.municipio for f in filas if f.municipio}),
        "barrios": sorted({f.barrio for f in filas if f.barrio}),
    }


def _calcular_resumen_plataforma() -> dict[str, int]:
    return {
        "productos": catalogo.productos_publicos().count(),
        "establecimientos": Establecimiento.objects.filter(activo=True).count(),
        "reportes": ReportePrecio.objects.filter(estado=ReportePrecio.Estado.PUBLICADO).count(),
    }


def resumen_plataforma() -> dict[str, int]:
    """Cifras de la portada. Se invalida junto con la comparación al registrar un precio."""
    return cache.get_or_set(clave_resumen(), _calcular_resumen_plataforma, ttl_comparacion())


def productos_destacados(limite: int = 8):
    """Productos con más reportes publicados (un solo query; sin criterio comercial)."""
    return list(
        catalogo.productos_publicos()
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
    if len(filas) < MIN_FILAS_EJEMPLO or len({f.unidad_base for f in filas}) != 1:
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
