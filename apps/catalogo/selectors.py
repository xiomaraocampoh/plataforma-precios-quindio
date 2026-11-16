"""Lecturas del catálogo (capa de aplicación): búsqueda, listado y posibles duplicados."""

import re

from django.db.models import Prefetch, Q

from .domain.duplicados import normalizar_nombre, son_posibles_duplicados
from .models import Categoria, Marca, Presentacion, Producto

MIN_CARACTERES_BUSQUEDA = 2
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


def buscar_productos(texto: str, limite: int = 10):
    """RF-04: por nombre o marca sin distinguir tildes ni mayúsculas, o por código de barras."""
    texto = (texto or "").strip()
    if es_codigo_de_barras(texto):
        filtro = Q(presentaciones__codigo_barras=texto, presentaciones__activa=True)
    else:
        if len(normalizar_nombre(texto)) < MIN_CARACTERES_BUSQUEDA:
            return Producto.objects.none()
        filtro = _por_texto(texto)
    productos = productos_publicos().filter(filtro).distinct()
    return productos.order_by("nombre", "marca__nombre")[:limite]


def listar_productos(*, texto: str = "", marca: str = "", categoria_id: int | None = None):
    """Listado con filtros de marca y categoría (RF-19, prioridad C). Orden alfabético."""
    activas = Presentacion.objects.filter(activa=True).order_by("unidad", "cantidad")
    productos = productos_publicos().prefetch_related(Prefetch("presentaciones", queryset=activas))
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
        productos_publicos()
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
