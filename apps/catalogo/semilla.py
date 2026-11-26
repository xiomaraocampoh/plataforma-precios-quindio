"""Siembra de prueba del catálogo: categorías, marcas, productos y presentaciones (ADR-0023).

La usan la migración `0008_semilla_catalogo` y `cargar_datos_prueba`. Recibe el registro de
modelos (`apps`), así que no importa modelos ni servicios. Como los modelos históricos de una
migración no ejecutan `save()` personalizado, el nombre normalizado se calcula aquí con la misma
función de dominio (D-05).

Idempotente: cada fila se busca por su clave natural antes de crearla.
"""

from pathlib import Path

from django.db import transaction
from django.db.models import ProtectedError

from apps.administracion.domain.datos_prueba import leer_presentacion, leer_si_no
from core.semilla import Resumen, filas, validar

from .domain.duplicados import normalizar_nombre, son_posibles_duplicados
from .domain.grupos import grupo_sugerido


def _limpio(texto: str) -> str:
    return " ".join((texto or "").split())


def _categorias(apps, directorio: Path, resumen: Resumen) -> dict:
    Categoria = apps.get_model("catalogo", "Categoria")
    resultado = {}
    for donde, fila in filas(directorio, "categorias.csv"):
        perecedera = validar(donde, lambda f: leer_si_no(f["perecedera"], campo="perecedera"), fila)
        nombre = _limpio(fila["nombre"])
        valores = {"perecedera": perecedera}
        if "grupo" in {
            c.name for c in Categoria._meta.get_fields()
        }:  # no existe en las migraciones viejas
            valores["grupo"] = grupo_sugerido(nombre)
        categoria, creada = Categoria.objects.get_or_create(nombre=nombre, defaults=valores)
        resultado[categoria.nombre] = categoria
        resumen.sumar("categorias", creada)
    return resultado


def _marcas(apps, directorio: Path, resumen: Resumen) -> dict:
    Marca = apps.get_model("catalogo", "Marca")
    resultado = {}
    for _, fila in filas(directorio, "marcas.csv"):
        nombre = _limpio(fila["nombre"])
        normal = normalizar_nombre(nombre)
        marca, creada = Marca.objects.get_or_create(
            nombre_normalizado=normal, defaults={"nombre": nombre}
        )
        resultado[normal] = marca
        resumen.sumar("marcas", creada)
    return resultado


def _producto(producto_modelo, nombre: str, marca, categoria) -> tuple[object | None, bool, str]:
    """(producto, creado, aviso). D-05: si solo hay uno PARECIDO de la misma marca no se crea."""
    normal = normalizar_nombre(nombre)
    existente = producto_modelo.objects.filter(nombre_normalizado=normal, marca=marca).first()
    if existente is not None:
        return existente, False, ""
    for otro in producto_modelo.objects.filter(marca=marca).only("id", "nombre"):
        if son_posibles_duplicados(nombre, otro.nombre):
            return None, False, f"«{nombre}» se parece a «{otro.nombre}» ({marca.nombre})."
    producto = producto_modelo.objects.create(
        nombre=nombre, nombre_normalizado=normal, marca=marca, categoria=categoria
    )
    return producto, True, ""


def _productos(apps, directorio, categorias, marcas, resumen) -> dict:
    Producto = apps.get_model("catalogo", "Producto")
    resultado = {}
    for donde, fila in filas(directorio, "productos.csv"):
        categoria = validar(donde, lambda f: categorias[_limpio(f["categoria"])], fila)
        marca = validar(donde, lambda f: marcas[normalizar_nombre(f["marca"])], fila)
        producto, creado, aviso = _producto(Producto, _limpio(fila["nombre"]), marca, categoria)
        if producto is None:
            resumen.avisos.append(f"{donde}: posible duplicado, no se creó. {aviso}")
            continue
        resultado[(marca.nombre_normalizado, producto.nombre_normalizado)] = producto
        resumen.sumar("productos", creado)
    return resultado


def _presentaciones(apps, directorio, productos, resumen) -> None:
    Presentacion = apps.get_model("catalogo", "Presentacion")
    for donde, fila in filas(directorio, "presentaciones.csv"):
        datos = validar(donde, leer_presentacion, fila)
        producto = productos.get(
            (normalizar_nombre(datos.marca), normalizar_nombre(datos.producto))
        )
        if producto is None:
            resumen.avisos.append(f"{donde}: el producto no se cargó; se omite la presentación.")
            continue
        presentacion, creada = Presentacion.objects.get_or_create(
            producto=producto,
            cantidad=datos.cantidad,
            unidad=datos.unidad,
            defaults={"codigo_barras": datos.codigo_barras},
        )
        if not creada and datos.codigo_barras and not presentacion.codigo_barras:
            presentacion.codigo_barras = datos.codigo_barras  # completa el código si faltaba
            presentacion.save(update_fields=["codigo_barras"])
        resumen.sumar("presentaciones", creada)


def sembrar(apps, *, directorio: Path, resumen: Resumen) -> dict:
    """Siembra el catálogo; devuelve las categorías por nombre (las usan las solicitudes)."""
    categorias = _categorias(apps, directorio, resumen)
    productos = _productos(
        apps, directorio, categorias, _marcas(apps, directorio, resumen), resumen
    )
    _presentaciones(apps, directorio, productos, resumen)
    return categorias


# ---------- reversa ----------


def _borrar_libres(objetos) -> int:
    """Borra cada objeto salvo los que algo protegido usa (un precio real, por ejemplo)."""
    borrados = 0
    for objeto in objetos:
        try:
            with transaction.atomic():  # punto de guardado: un fallo no aborta la migración
                objeto.delete()
        except ProtectedError:
            continue
        borrados += 1
    return borrados


def revertir(apps, *, directorio: Path) -> dict[str, int]:
    """Quita lo sembrado por clave natural. Lo que otro dato usa se conserva."""
    Producto = apps.get_model("catalogo", "Producto")
    Marca = apps.get_model("catalogo", "Marca")
    Categoria = apps.get_model("catalogo", "Categoria")
    claves = {
        (normalizar_nombre(f["marca"]), normalizar_nombre(f["nombre"]))
        for _, f in filas(directorio, "productos.csv")
    }
    candidatos = Producto.objects.select_related("marca").filter(
        nombre_normalizado__in={nombre for _, nombre in claves}, marca__isnull=False
    )
    productos = [
        p for p in candidatos if (p.marca.nombre_normalizado, p.nombre_normalizado) in claves
    ]
    marcas = {normalizar_nombre(f["nombre"]) for _, f in filas(directorio, "marcas.csv")}
    categorias = {_limpio(f["nombre"]) for _, f in filas(directorio, "categorias.csv")}
    return {
        "productos": _borrar_libres(productos),  # sus presentaciones caen en cascada
        "marcas": _borrar_libres(Marca.objects.filter(nombre_normalizado__in=marcas)),
        "categorias": _borrar_libres(Categoria.objects.filter(nombre__in=categorias)),
    }
