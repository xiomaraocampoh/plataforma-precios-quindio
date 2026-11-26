"""Consultas del lado lectura (Consumidores). Capa de aplicación — solo lectura.

Separación lectura/escritura "CQRS ligero": misma BD, caminos de código distintos.
Si la prueba de carga (EC-04) no alcanza p95 ≤ 2 s, el siguiente paso es una vista
materializada / tabla de lectura alimentada por los servicios de escritura (ver ADR-0002).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from urllib.parse import urlencode

from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from apps.catalogo import selectors as catalogo
from apps.catalogo.domain.normalizacion import a_unidad_base, formatear_cantidad, precio_por_unidad
from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.establecimientos.domain.mapas import enlace_mapa
from apps.establecimientos.models import Establecimiento
from apps.establecimientos.selectors import establecimiento_de_etiqueta
from apps.integraciones.domain.escaneo import ResultadoEscaneo, TipoEscaneo
from apps.integraciones.domain.etiqueta import EtiquetaPrecio
from apps.moderacion.selectors import denunciados_por
from apps.precios.domain.confianza import nivel_confianza
from apps.precios.domain.vigencia import Fuente, es_vigente, fecha_de_referencia
from apps.precios.models import ReportePrecio
from apps.precios.selectors import (
    confirmaciones_por_reporte,
    confirmados_hoy,
    politica_vigencia,
    reportes_propios,
    ultimo_establecimiento_id,
)
from core.cache import clave_comparacion, clave_resumen, ttl_comparacion
from core.extensiones import extensiones

from .domain.extensiones import (
    PUNTO_DATOS_COMERCIALES,
    DatosComerciales,
    PrecioOficialVigente,
    PromocionComparacion,
    reunir_datos,
)
from .domain.filtros import FiltroPrecio, FiltroUbicacion, filtrar, filtrar_por_precio
from .domain.oficial import discrepancia
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

log = logging.getLogger("ahorrapues.comparacion")


def buscar_productos(texto: str, limite: int = 10):
    """RF-04: la búsqueda vive en el catálogo; aquí solo se reexpone para las vistas."""
    return catalogo.buscar_productos(texto, limite)


@dataclass(frozen=True)
class FilaComparacion:
    """Un resultado de la comparación y los datos que la tarjeta necesita a su lado (RF-16).

    El orden lo fija SOLO `ordenar_neutral` sobre los `ResultadoComparacion` (EC-06); estos datos
    extra (producto, comercio, dirección, mapa, confirmación) nunca entran en la clave de orden.
    Del autor no hay nada: ni nombre, ni usuario, ni ubicación (M-15, EC-15).
    """

    resultado: ResultadoComparacion
    reporte_id: int
    municipio: str
    barrio: str
    ultima_confirmacion: datetime | None
    producto: str = ""
    presentacion_id: int = 0  # precarga «Registrar precio aquí»
    producto_id: int = 0
    marca: str = ""
    cantidad: Decimal = Decimal("0")
    unidad: str = ""
    tipo: str = ""
    direccion: str = ""
    enlace_mapa: str | None = None
    # Módulo comercial por el puerto (ADR-012, ADR-018, ADR-014). Nunca entran en el orden.
    es_oficial: bool = False
    usuarios_reportan: Decimal | None = None  # discrepancia del ADR-018
    promociones: tuple[PromocionComparacion, ...] = ()

    @property
    def ancla(self) -> str:
        """Id de la tarjeta: la fila oficial no tiene reporte propio."""
        if self.reporte_id:
            return f"tp-{self.reporte_id}"
        return f"tpo-{self.resultado.establecimiento_id}-{self.presentacion_id}"

    @property
    def usuarios_reportan_texto(self) -> str:
        if self.usuarios_reportan is None:
            return ""
        return f"Usuarios reportan {formatear_pesos(self.usuarios_reportan)}"

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


def _reportes_candidatos(
    producto_ids: list[int] | None, desde: datetime, establecimiento_id: int | None = None
):
    # Un reporte viejo confirmado hace poco con «Sigue igual» sigue siendo candidato (RF-14)
    candidatos = ReportePrecio.objects.filter(
        Q(fecha_observacion__gte=desde) | Q(confirmaciones__creado_en__gte=desde),
        presentacion__activa=True,  # una presentación retirada del catálogo no se compara
        estado=ReportePrecio.Estado.PUBLICADO,
        establecimiento__activo=True,
    )
    if producto_ids is not None:
        candidatos = candidatos.filter(presentacion__producto_id__in=producto_ids)
    if establecimiento_id is not None:
        candidatos = candidatos.filter(establecimiento_id=establecimiento_id)
    return (
        candidatos.select_related(
            "presentacion__producto__categoria", "presentacion__producto__marca", "establecimiento"
        )
        .order_by("establecimiento_id", "presentacion_id", "-fecha_observacion")
        .distinct()
    )


def _ultimos_por_par(producto_ids: list[int], desde: datetime):
    """El reporte más reciente por (local, presentación), cuántos anteriores dicen lo mismo y
    todos los (precio, fecha) del par, que la discrepancia del ADR-018 necesita."""
    ultimos: dict[tuple[int, int], ReportePrecio] = {}
    iguales: dict[tuple[int, int], int] = {}
    todos: dict[tuple[int, int], list[tuple[Decimal, datetime]]] = {}
    for r in _reportes_candidatos(producto_ids, desde):  # un solo query; agrupación en memoria
        clave = (r.establecimiento_id, r.presentacion_id)
        todos.setdefault(clave, []).append((r.precio, r.fecha_observacion))
        if clave not in ultimos:
            ultimos[clave] = r
            iguales[clave] = 0
        elif r.precio == ultimos[clave].precio:
            iguales[clave] += 1
    return ultimos, iguales, todos


def _fila(r: ReportePrecio, resultado: ResultadoComparacion, ultima) -> FilaComparacion:
    return _fila_de(r.establecimiento, r.presentacion, resultado, reporte_id=r.pk, ultima=ultima)


def _fila_de(
    local, presentacion, resultado: ResultadoComparacion, *, reporte_id=0, ultima=None, **extra
) -> FilaComparacion:
    return FilaComparacion(
        resultado=resultado,
        reporte_id=reporte_id,
        municipio=local.municipio,
        barrio=local.barrio,
        ultima_confirmacion=ultima,
        producto=presentacion.producto.nombre,
        presentacion_id=presentacion.pk,
        producto_id=presentacion.producto_id,
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
        **extra,
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


def _datos_comerciales(producto_ids: list[int], ahora: datetime) -> DatosComerciales:
    """Lo que aportan las extensiones registradas (módulo comercial). Si una falla, la comparación
    sigue con lo reportado: el núcleo no depende de ella (EC-05)."""
    try:
        return reunir_datos(extensiones(PUNTO_DATOS_COMERCIALES), producto_ids, ahora)
    except Exception:  # una extensión rota no debe tumbar la comparación
        log.exception("Una extensión de la comparación falló; se muestran solo los reportes.")
        return DatosComerciales()


def _oficiales_vigentes(datos: DatosComerciales, ahora, politica) -> dict:
    """ADR-018: solo el oficial confirmado en los últimos 30 días (fuente «comercio»)."""
    return {
        par: o
        for par, o in datos.oficiales_por_par().items()
        if es_vigente(min(o.confirmado_en, ahora), ahora, Fuente.COMERCIO, politica=politica)
    }


def _objetos_de(oficiales: dict, ultimos: dict) -> tuple[dict, dict]:
    """Establecimiento y presentación de cada par oficial: de los reportes ya leídos o, si no hay
    reporte del par, en dos queries más (activos y públicos, como en los reportes)."""
    faltan = [par for par in oficiales if par not in ultimos]
    locales = {r.establecimiento_id: r.establecimiento for r in ultimos.values()}
    presentaciones = {r.presentacion_id: r.presentacion for r in ultimos.values()}
    if faltan:
        locales |= Establecimiento.objects.filter(
            pk__in={e for e, _ in faltan}, activo=True
        ).in_bulk()
        presentaciones |= (
            catalogo.presentaciones_publicas()
            .filter(pk__in={p for _, p in faltan})
            .select_related("producto__categoria", "producto__marca")
            .in_bulk()
        )
    return locales, presentaciones


def _fila_oficial(o: PrecioOficialVigente, local, presentacion, reportes, promos, ahora):
    """El precio oficial verificado es el principal; la discrepancia baja la confianza a media."""
    aviso = discrepancia(o.precio, reportes, ahora)
    unitario, base = precio_por_unidad(o.precio, presentacion.cantidad, presentacion.unidad)
    confianza = nivel_confianza(Fuente.COMERCIO, 0, False).value if aviso is None else "media"
    resultado = ResultadoComparacion(
        establecimiento_id=local.pk,
        establecimiento=local.nombre,
        presentacion=str(presentacion),
        precio=o.precio,
        precio_unitario=unitario,
        unidad_base=base.value,
        fuente=Fuente.COMERCIO.value,
        confianza=confianza,
        fecha_observacion=o.confirmado_en,
        es_promocion=bool(promos),  # etiqueta: no altera el orden (EC-06)
    )
    return _fila_de(
        local,
        presentacion,
        resultado,
        es_oficial=True,
        usuarios_reportan=aviso,
        promociones=tuple(promos),
    )


def _filas_oficiales(datos, oficiales, ultimos, todos, ahora):
    """(producto, par, fila) de cada oficial vigente con local y presentación activos."""
    locales, presentaciones = _objetos_de(oficiales, ultimos)
    promos = datos.promociones_por_par()
    for par, o in oficiales.items():
        local, presentacion = locales.get(par[0]), presentaciones.get(par[1])
        if local is None or presentacion is None:  # inactivo o retirado del catálogo
            continue
        fila = _fila_oficial(o, local, presentacion, todos.get(par, []), promos.get(par, []), ahora)
        yield o.producto_id, par, fila


def _calcular_filas_de(producto_ids: list[int]) -> dict[int, list[FilaComparacion]]:
    """Filas vigentes de varios productos con un número constante de queries (sin N+1).

    Si un comercio verificado tiene precio oficial vigente para un (local, presentación), esa fila
    reemplaza a la del reporte (ADR-018). El orden sigue siendo SOLO `ordenar_neutral` (EC-06).
    """
    ahora = timezone.now()
    politica = politica_vigencia()
    desde = ahora - timedelta(days=max(politica.dias_reporte, politica.dias_oficial))
    ultimos, iguales, todos = _ultimos_por_par(producto_ids, desde)
    confirmaciones = confirmaciones_por_reporte([r.pk for r in ultimos.values()])
    datos = _datos_comerciales(producto_ids, ahora)
    oficiales = _oficiales_vigentes(datos, ahora, politica)

    por_producto: dict[int, dict[ResultadoComparacion, FilaComparacion]] = {
        pid: {} for pid in producto_ids
    }
    con_oficial: set[tuple[int, int]] = set()
    for pid, par, fila in _filas_oficiales(datos, oficiales, ultimos, todos, ahora):
        if pid in por_producto:
            por_producto[pid][fila.resultado] = fila
            con_oficial.add(par)
    for clave, r in ultimos.items():
        if clave in con_oficial:
            continue  # el oficial verificado es el principal (ADR-018)
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


def filas_de_establecimiento(establecimiento_id: int) -> list[FilaComparacion]:
    """Precios vigentes de UN comercio, en orden alfabético por producto.

    No es un ranking: no compara comercios entre sí (eso es `comparar_filas` y su orden neutral,
    EC-06). Reutiliza el cálculo de la comparación (incluido el precio oficial, ADR-018), así que
    esta página y la comparación nunca muestran precios distintos para el mismo comercio.
    """
    politica = politica_vigencia()
    desde = timezone.now() - timedelta(days=max(politica.dias_reporte, politica.dias_oficial))
    productos = {
        r.presentacion.producto_id for r in _reportes_candidatos(None, desde, establecimiento_id)
    }
    filas = [
        fila
        for por_producto in _calcular_filas_de(sorted(productos)).values()
        for fila in por_producto
        if fila.resultado.establecimiento_id == establecimiento_id
    ]
    return sorted(
        filas, key=lambda f: (f.producto.casefold(), f.marca.casefold(), f.unidad, f.cantidad)
    )


def _calcular_filas(producto_id: int) -> list[FilaComparacion]:
    return _calcular_filas_de([producto_id])[producto_id]


def comparar_filas(producto_id: int) -> list[FilaComparacion]:
    """Cache-aside: TTL corto (D-01 ≤ 1 min) + invalidación al registrar o confirmar."""
    return cache.get_or_set(
        clave_comparacion(producto_id),
        lambda: _calcular_filas(producto_id),
        ttl_comparacion(),
    )


def filas_vigentes_de(producto_ids: list[int]) -> dict[int, list[FilaComparacion]]:
    """Filas vigentes de varios productos, en el orden neutral de cada uno (ADR-0027).

    Usa la misma caché por producto que la comparación y calcula las que faltan en un solo lote:
    un precio nuevo invalida la clave del producto y la siguiente consulta ya lo ve (EC-02).
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
    return {pid: en_cache.get(clave, calculadas.get(pid, [])) for clave, pid in claves.items()}


def primeras_filas(producto_ids: list[int]) -> dict[int, FilaComparacion | None]:
    """Listado de productos: la primera fila en el orden neutral de cada uno (o None)."""
    return {
        pid: (filas[0] if filas else None) for pid, filas in filas_vigentes_de(producto_ids).items()
    }


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


def categorias_frecuentes(limite: int = 4):
    """Categorías con más precios publicados, para los accesos rápidos de la portada.

    Solo mide la actividad de la comunidad (sin criterio comercial); empata por nombre.
    """
    return list(
        Categoria.objects.filter(activa=True)
        .annotate(
            n_reportes=Count(
                "productos__presentaciones__reportes",
                filter=Q(
                    productos__activo=True,
                    productos__presentaciones__reportes__estado=ReportePrecio.Estado.PUBLICADO,
                ),
            )
        )
        .filter(n_reportes__gt=0)
        .order_by("-n_reportes", "nombre")[:limite]
    )


def productos_destacados(limite: int = 8):
    """Productos con más reportes publicados (un solo query; sin criterio comercial)."""
    return list(
        catalogo.con_fotos(catalogo.productos_publicos())
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


# ───────────── Escáner en vivo (ADR-0026) ─────────────


@dataclass(frozen=True)
class PropuestaEscaneo:
    """Lo que la hoja del escáner muestra. Todo sale del catálogo y del directorio; de la IA solo
    se usa lo leído para buscar, y el precio por unidad se CALCULA (`precio_por_unidad`)."""

    tipo: str
    producto: Producto | None = None
    presentacion: Presentacion | None = None
    etiqueta: EtiquetaPrecio | None = None
    nombre: str = ""
    marca: str = ""
    cantidad_texto: str = ""
    precio_texto: str = ""
    precio_anterior_texto: str = ""
    por_unidad_texto: str = ""
    impreso_texto: str = ""
    establecimiento: Establecimiento | None = None
    establecimiento_leido: bool = False  # True: la tienda salió de la etiqueta
    consulta_registrar: str = ""
    consulta_solicitar: str = ""
    consulta_sugerir: str = ""


def _presentacion_de(producto: Producto, cantidad, unidad, codigo: str) -> Presentacion | None:
    """La presentación del catálogo que es la de la etiqueta (código, o la misma cantidad en la
    unidad base: 1000 g = 1 kg). Si no hay una exacta, la persona elige: no se adivina (M-02)."""
    presentaciones = list(catalogo.presentaciones_publicas().filter(producto=producto))
    if codigo:
        por_codigo = [p for p in presentaciones if p.codigo_barras == codigo]
        if por_codigo:
            return por_codigo[0]
    if cantidad is None or not unidad:
        return None
    buscada = a_unidad_base(Decimal(cantidad), unidad)
    iguales = [p for p in presentaciones if a_unidad_base(p.cantidad, p.unidad) == buscada]
    return iguales[0] if len(iguales) == 1 else None


def _textos_de_precio(etiqueta: EtiquetaPrecio, presentacion: Presentacion | None) -> dict:
    cantidad, unidad = (
        (presentacion.cantidad, presentacion.unidad)
        if presentacion
        else (etiqueta.cantidad, etiqueta.unidad)
    )
    textos = {"precio_texto": formatear_pesos(etiqueta.precio)}
    if etiqueta.precio_anterior:
        textos["precio_anterior_texto"] = formatear_pesos(etiqueta.precio_anterior)
    if cantidad and unidad:
        valor, base = precio_por_unidad(etiqueta.precio, cantidad, unidad)
        textos["por_unidad_texto"] = texto_por_unidad(valor, base)
    if etiqueta.precio_por_unidad_impreso:
        impreso = formatear_pesos(etiqueta.precio_por_unidad_impreso)
        textos["impreso_texto"] = f"{impreso} por {etiqueta.unidad_impresa}"
    return textos


def _tienda_propuesta(etiqueta: EtiquetaPrecio, usuario) -> tuple[Establecimiento | None, bool]:
    """La tienda que dice la etiqueta si está en el directorio; si no, la última de la persona.
    Nunca se crea una (RF-09)."""
    leida = establecimiento_de_etiqueta(etiqueta.establecimiento_texto)
    if leida is not None:
        return leida, True
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return None, False
    ultima = ultimo_establecimiento_id(usuario)
    return Establecimiento.objects.filter(pk=ultima).first() if ultima else None, False


def _consulta_solicitar(nombre, marca, cantidad, unidad, codigo) -> str:
    datos = {"nombre": nombre, "marca": marca, "codigo_barras": codigo}
    if cantidad and unidad:
        datos.update(cantidad=format(Decimal(cantidad).normalize(), "f"), unidad=unidad)
    return urlencode({k: v for k, v in datos.items() if v})


def _propuesta_etiqueta(resultado: ResultadoEscaneo, producto, usuario) -> PropuestaEscaneo:
    etiqueta = resultado.etiqueta
    presentacion = (
        _presentacion_de(producto, etiqueta.cantidad, etiqueta.unidad, etiqueta.codigo_barras)
        if producto
        else None
    )
    tienda, leida = _tienda_propuesta(etiqueta, usuario)
    registrar = {"precio": format(etiqueta.precio.normalize(), "f"), "origen": "etiqueta"}
    if producto:
        registrar["producto"] = producto.pk
    if presentacion:
        registrar["presentacion"] = presentacion.pk
    if tienda:
        registrar["establecimiento"] = tienda.pk
    cantidad = (
        f"{formatear_cantidad(etiqueta.cantidad)} {etiqueta.unidad}" if etiqueta.cantidad else ""
    )
    return PropuestaEscaneo(
        tipo=TipoEscaneo.ETIQUETA,
        producto=producto,
        presentacion=presentacion,
        etiqueta=etiqueta,
        nombre=etiqueta.nombre,
        marca=etiqueta.marca,
        cantidad_texto=cantidad,
        establecimiento=tienda,
        establecimiento_leido=leida,
        consulta_registrar=urlencode(registrar),
        consulta_solicitar=_consulta_solicitar(
            etiqueta.nombre,
            etiqueta.marca,
            etiqueta.cantidad,
            etiqueta.unidad,
            etiqueta.codigo_barras,
        ),
        consulta_sugerir=urlencode({"nombre": etiqueta.establecimiento_texto})
        if etiqueta.establecimiento_texto and not leida
        else "",
        **_textos_de_precio(etiqueta, presentacion),
    )


def propuesta_de_escaneo(resultado: ResultadoEscaneo, usuario) -> PropuestaEscaneo | None:
    """Qué ofrecer tras reconocer un fotograma, o None si no hay nada que mostrar.

    Elegir el producto no toca el orden neutral de la comparación (EC-06): solo decide qué
    comparación abrir."""
    if resultado.tipo == TipoEscaneo.NADA or resultado.pista is None and not resultado.etiqueta:
        return None
    pista = resultado.pista
    candidatos = (
        catalogo.buscar_por_pista(
            nombre=pista.nombre,
            marca=pista.marca,
            cantidad=pista.cantidad,
            unidad=pista.unidad,
            codigo=pista.codigo_barras,
            limite=1,
        )
        if pista
        else []
    )
    producto = candidatos[0] if candidatos else None
    if resultado.tipo == TipoEscaneo.ETIQUETA:
        return _propuesta_etiqueta(resultado, producto, usuario)
    return PropuestaEscaneo(
        tipo=TipoEscaneo.PRODUCTO,
        producto=producto,
        nombre=pista.nombre,
        marca=pista.marca,
        cantidad_texto=f"{pista.cantidad} {pista.unidad}" if pista.cantidad else "",
        consulta_solicitar=_consulta_solicitar(
            pista.nombre, pista.marca, pista.cantidad, pista.unidad, pista.codigo_barras
        ),
    )
