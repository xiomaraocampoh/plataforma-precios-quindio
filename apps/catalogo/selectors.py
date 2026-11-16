"""Lecturas del catálogo (capa de aplicación): búsqueda, listado y posibles duplicados."""

import re

from django.db.models import Prefetch, Q

from .domain.duplicados import normalizar_nombre, son_posibles_duplicados
from .models import Categoria, Presentacion, Producto

MIN_CARACTERES_BUSQUEDA = 2
_CODIGO_DE_BARRAS = re.compile(r"^\d{8,14}$")  # EAN-8, UPC-A, EAN-13, GTIN-14


def es_codigo_de_barras(texto: str) -> bool:
    return bool(_CODIGO_DE_BARRAS.match(texto.strip()))


def productos_por_codigo(codigo: str):
    """RF-04: productos con una presentación de ese código de barras exacto (sin repetir)."""
    return (
        Producto.objects.filter(presentaciones__codigo_barras=codigo)
        .select_related("categoria")
        .distinct()
        .order_by("nombre", "marca")
    )


def buscar_productos(texto: str, limite: int = 10):
    """RF-04: por nombre sin distinguir tildes ni mayúsculas, o por código de barras exacto."""
    texto = (texto or "").strip()
    if es_codigo_de_barras(texto):
        filtro = Q(presentaciones__codigo_barras=texto)
    else:
        normal = normalizar_nombre(texto)
        if len(normal) < MIN_CARACTERES_BUSQUEDA:
            return Producto.objects.none()
        filtro = Q(nombre_normalizado__contains=normal) | Q(marca__icontains=texto)
    return (
        Producto.objects.filter(filtro)
        .select_related("categoria")
        .distinct()
        .order_by("nombre", "marca")[:limite]
    )


def listar_productos(*, texto: str = "", marca: str = "", categoria_id: int | None = None):
    """Listado con filtros de marca y categoría (RF-19, prioridad C). Orden alfabético."""
    productos = Producto.objects.select_related("categoria").prefetch_related(
        Prefetch("presentaciones", queryset=Presentacion.objects.order_by("unidad", "cantidad"))
    )
    texto = (texto or "").strip()
    if es_codigo_de_barras(texto):
        productos = productos.filter(presentaciones__codigo_barras=texto)
    elif normalizar_nombre(texto):
        productos = productos.filter(
            Q(nombre_normalizado__contains=normalizar_nombre(texto)) | Q(marca__icontains=texto)
        )
    if marca:
        productos = productos.filter(marca__iexact=marca)
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    return productos.distinct().order_by("nombre", "marca")


def opciones_de_filtro() -> dict:
    marcas = (
        Producto.objects.exclude(marca="")
        .order_by("marca")
        .values_list("marca", flat=True)
        .distinct()
    )
    return {"marcas": list(marcas), "categorias": list(Categoria.objects.order_by("nombre"))}


def obtener_producto(producto_id: int) -> Producto | None:
    return (
        Producto.objects.select_related("categoria")
        .prefetch_related("presentaciones")
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
        for p in Producto.objects.only("id", "nombre", "marca", "nombre_normalizado")
        if son_posibles_duplicados(nombre, p.nombre)
    ]
    return similares[0] if len(similares) == 1 else None


def productos_similares(nombre: str, marca: str = "", limite: int = 5) -> list[Producto]:
    """RF-06, D-05: productos cuyo nombre (con la marca) se parece ≥ 0,85 al solicitado."""
    buscado = f"{nombre} {marca}".strip()
    if not normalizar_nombre(buscado):
        return []
    candidatos = Producto.objects.select_related("categoria").only(
        "id", "nombre", "marca", "categoria__nombre"
    )
    similares = [
        p
        for p in candidatos
        if son_posibles_duplicados(buscado, str(p)) or son_posibles_duplicados(nombre, p.nombre)
    ]
    return sorted(similares, key=lambda p: (p.nombre, p.marca))[:limite]
