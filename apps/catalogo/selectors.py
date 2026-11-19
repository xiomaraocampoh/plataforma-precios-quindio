"""Lecturas del catálogo (capa de aplicación): búsqueda, listado y posibles duplicados."""

import re

from django.conf import settings
from django.db.models import Prefetch, Q

from .domain.codigo_barras import es_gtin_valido
from .domain.coincidencia import (
    UMBRAL_CANDIDATO,
    palabras_significativas,
    puntuar_coincidencia,
    similitud_marca,
)
from .domain.duplicados import normalizar_nombre, son_posibles_duplicados
from .models import Categoria, FotoProducto, Marca, Presentacion, Producto

MIN_CARACTERES_BUSQUEDA = 2
TOPE_PRESELECCION = 200  # candidatos que se puntúan en Python (búsqueda por foto)
MIN_LETRAS_PALABRA = 3  # «n», «5»: demasiado cortas para preseleccionar en la base
_CODIGO_DE_BARRAS = re.compile(r"^\d{8,14}$")  # EAN-8, UPC-A, EAN-13, GTIN-14


def es_codigo_de_barras(texto: str) -> bool:
    return bool(_CODIGO_DE_BARRAS.match(texto.strip()))


def productos_publicos():
    """Lo que ve el público: productos activos de una categoría activa (con su marca, sin N+1)."""
    return Producto.objects.filter(activo=True, categoria__activa=True).select_related(
        "categoria", "marca"
    )


def presentaciones_publicas():
    """Presentaciones que se pueden registrar y comparar: activas y de un producto público."""
    return Presentacion.objects.filter(
        activa=True, producto__activo=True, producto__categoria__activa=True
    )


def _por_texto(texto: str) -> Q:
    normal = normalizar_nombre(texto)
    return Q(nombre_normalizado__contains=normal) | Q(marca__nombre_normalizado__contains=normal)


def _con_presentaciones():
    activas = Presentacion.objects.filter(activa=True).order_by("unidad", "cantidad")
    return productos_publicos().prefetch_related(Prefetch("presentaciones", queryset=activas))


def _preseleccion(nombre: str, marca: str, excluir: list[int]) -> list[Producto]:
    """Sin traer todo el catálogo: nombre con alguna palabra significativa O marca parecida."""
    filtro = Q(pk__in=[])
    for palabra in palabras_significativas(nombre):
        if len(palabra) >= MIN_LETRAS_PALABRA:
            filtro |= Q(nombre_normalizado__contains=palabra)
    for palabra in palabras_significativas(marca):
        if len(palabra) >= MIN_LETRAS_PALABRA:
            filtro |= Q(marca__nombre_normalizado__icontains=palabra)
    productos = _con_presentaciones().filter(filtro).exclude(pk__in=excluir).distinct()
    return list(productos.order_by("pk")[:TOPE_PRESELECCION])


def _puntuar(productos, nombre, marca, cantidad, unidad) -> list[tuple[float, Producto]]:
    # Una marca que no está entre los candidatos (la IA la leyó mal) no castiga a los demás
    if not any(p.marca and similitud_marca(marca, p.marca.nombre) for p in productos):
        marca = ""
    return [
        (
            puntuar_coincidencia(
                nombre,
                marca,
                cantidad,
                unidad,
                p.nombre,
                p.marca.nombre if p.marca else "",
                [(x.cantidad, x.unidad) for x in p.presentaciones.all()],
            ),
            p,
        )
        for p in productos
    ]


def buscar_por_pista(
    *,
    nombre: str,
    marca: str = "",
    cantidad: str = "",
    unidad: str = "",
    codigo: str = "",
    limite: int = 5,
) -> list[Producto]:
    """Búsqueda por foto (ADR-022): los productos más parecidos a la pista, el mejor primero.

    Solo elige qué producto abrir; no cambia el orden neutral de la comparación (EC-06).
    Un código de barras válido y existente va primero. Consultas constantes (sin N+1).
    """
    umbral = getattr(settings, "UMBRAL_COINCIDENCIA_FOTO", UMBRAL_CANDIDATO)
    codigo = (codigo or "").strip()
    primero = []
    if codigo and es_gtin_valido(codigo):
        por_codigo = _con_presentaciones().filter(
            presentaciones__codigo_barras=codigo, presentaciones__activa=True
        )
        primero = list(por_codigo.distinct().order_by("nombre", "marca__nombre")[:limite])
    candidatos = _preseleccion(nombre, marca, [p.pk for p in primero])
    puntuados = [x for x in _puntuar(candidatos, nombre, marca, cantidad, unidad) if x[0] >= umbral]
    puntuados.sort(key=lambda x: (-x[0], x[1].nombre_normalizado, x[1].marca_id or 0, x[1].pk))
    return (primero + [p for _, p in puntuados])[:limite]


def productos_por_codigo(codigo: str):
    """RF-04: productos con una presentación de ese código de barras exacto (sin repetir)."""
    return (
        productos_publicos()
        .filter(presentaciones__codigo_barras=codigo)
        .distinct()
        .order_by("nombre", "marca__nombre")
    )


def buscar_productos(texto: str, limite: int = 10):
    """RF-04: por nombre o marca sin distinguir tildes ni mayúsculas, o por código de barras."""
    texto = (texto or "").strip()
    if es_codigo_de_barras(texto):
        filtro = Q(presentaciones__codigo_barras=texto, presentaciones__activa=True)
    else:
        if len(normalizar_nombre(texto)) < MIN_CARACTERES_BUSQUEDA:
            return Producto.objects.none()
        filtro = _por_texto(texto)
    productos = con_fotos(productos_publicos()).filter(filtro).distinct()
    return productos.order_by("nombre", "marca__nombre")[:limite]


def listar_productos(*, texto: str = "", marca: str = "", categoria_id: int | None = None):
    """Listado con filtros de marca y categoría (RF-19, prioridad C). Orden alfabético."""
    activas = Presentacion.objects.filter(activa=True).order_by("unidad", "cantidad")
    productos = con_fotos(productos_publicos()).prefetch_related(
        Prefetch("presentaciones", queryset=activas)
    )
    texto = (texto or "").strip()
    if es_codigo_de_barras(texto):
        productos = productos.filter(presentaciones__codigo_barras=texto)
    elif normalizar_nombre(texto):
        productos = productos.filter(_por_texto(texto))
    if marca:
        productos = productos.filter(marca__nombre_normalizado=normalizar_nombre(marca))
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    return productos.distinct().order_by("nombre", "marca__nombre")


def opciones_de_filtro() -> dict:
    marcas = (
        Marca.objects.filter(activa=True, productos__activo=True)
        .order_by("nombre")
        .values_list("nombre", flat=True)
        .distinct()
    )
    return {
        "marcas": list(marcas),
        "categorias": list(Categoria.objects.filter(activa=True).order_by("nombre")),
    }


def obtener_producto(producto_id: int) -> Producto | None:
    activas = Presentacion.objects.filter(activa=True)
    return (
        con_fotos(productos_publicos())
        .prefetch_related(Prefetch("presentaciones", queryset=activas))
        .filter(pk=producto_id)
        .first()
    )


def producto_por_nombre(nombre: str) -> Producto | None:
    """Producto con ese nombre normalizado; si no hay, el único con similitud ≥ 0,85 (D-05)."""
    normal = normalizar_nombre(nombre)
    if not normal:
        return None
    exactos = list(Producto.objects.filter(nombre_normalizado=normal)[:2])
    if len(exactos) == 1:
        return exactos[0]
    similares = [
        p
        for p in Producto.objects.only("id", "nombre", "nombre_normalizado")
        if son_posibles_duplicados(nombre, p.nombre)
    ]
    return similares[0] if len(similares) == 1 else None


def productos_similares(nombre: str, marca: str = "", limite: int = 5) -> list[Producto]:
    """RF-06, D-05: productos cuyo nombre (con la marca) se parece ≥ 0,85 al solicitado."""
    buscado = f"{nombre} {marca}".strip()
    if not normalizar_nombre(buscado):
        return []
    candidatos = Producto.objects.select_related("categoria", "marca").only(
        "id", "nombre", "marca__nombre", "categoria__nombre"
    )
    similares = [
        p
        for p in candidatos
        if son_posibles_duplicados(buscado, str(p)) or son_posibles_duplicados(nombre, p.nombre)
    ]
    return sorted(similares, key=lambda p: (p.nombre, str(p.marca or "")))[:limite]


def foto_de(producto_id: int) -> tuple[bytes, str, str] | None:
    """(bytes, tipo, versión) de la foto de un producto público; None si no hay o está retirado."""
    fila = (
        FotoProducto.objects.filter(
            producto_id=producto_id, producto__activo=True, producto__categoria__activa=True
        )
        .values_list("contenido", "tipo_contenido", "version")
        .first()
    )
    if fila is None:
        return None
    contenido, tipo, version = fila
    return bytes(contenido), tipo, version  # PostgreSQL entrega memoryview


def con_fotos(productos):
    """Agrega la foto de cada producto en el mismo query, SIN traer los bytes (sin N+1, EC-01)."""
    return productos.select_related("foto").defer("foto__contenido")
