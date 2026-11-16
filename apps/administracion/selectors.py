"""Lecturas del panel: listados con búsqueda y filtros (incluye lo inactivo, a diferencia del
catálogo público). Cada listado usa select_related/annotate: un número fijo de consultas."""

from django.db import router
from django.db.models import Count, Q
from django.db.models.deletion import Collector, ProtectedError, RestrictedError

from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Marca, Producto
from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento

from .models import RegistroAuditoria

MODELOS = {
    "marca": Marca,
    "categoria": Categoria,
    "producto": Producto,
    "establecimiento": Establecimiento,
}
_SI_NO = {"si": True, "no": False}


def _si_no(valor: str) -> bool | None:
    return _SI_NO.get(valor)


def _entero(valor: str) -> int | None:
    return int(valor) if str(valor).isdigit() else None


def obtener(entidad: str, pk: int):
    return MODELOS[entidad].objects.filter(pk=pk).first()


def obtener_usuario(pk: int) -> Usuario | None:
    return Usuario.objects.filter(pk=pk).first()


def puede_eliminarse(objeto) -> bool:
    """True si nada protegido lo referencia (reportes, productos, solicitudes). No borra nada."""
    collector = Collector(using=router.db_for_write(type(objeto)))
    try:
        collector.collect([objeto])
    except (ProtectedError, RestrictedError):
        return False
    return True


def listar_marcas(*, texto: str = "", activa: str = ""):
    marcas = Marca.objects.annotate(n_productos=Count("productos"))
    if normalizar_nombre(texto):
        marcas = marcas.filter(nombre_normalizado__contains=normalizar_nombre(texto))
    if _si_no(activa) is not None:
        marcas = marcas.filter(activa=_si_no(activa))
    return marcas.order_by("nombre")


def listar_categorias(*, texto: str = "", activa: str = "", perecedera: str = ""):
    categorias = Categoria.objects.annotate(n_productos=Count("productos"))
    if texto.strip():
        categorias = categorias.filter(nombre__icontains=texto.strip())
    if _si_no(activa) is not None:
        categorias = categorias.filter(activa=_si_no(activa))
    if _si_no(perecedera) is not None:
        categorias = categorias.filter(perecedera=_si_no(perecedera))
    return categorias.order_by("nombre")


def listar_productos(*, texto: str = "", marca: str = "", categoria: str = "", activo: str = ""):
    productos = Producto.objects.select_related("marca", "categoria").annotate(
        n_presentaciones=Count("presentaciones", distinct=True)
    )
    texto = texto.strip()
    if texto.isdigit() and len(texto) >= 8:
        productos = productos.filter(presentaciones__codigo_barras=texto)
    elif normalizar_nombre(texto):
        normal = normalizar_nombre(texto)
        productos = productos.filter(
            Q(nombre_normalizado__contains=normal) | Q(marca__nombre_normalizado__contains=normal)
        )
    if _entero(marca):
        productos = productos.filter(marca_id=_entero(marca))
    if _entero(categoria):
        productos = productos.filter(categoria_id=_entero(categoria))
    if _si_no(activo) is not None:
        productos = productos.filter(activo=_si_no(activo))
    return productos.order_by("nombre", "marca__nombre")


def listar_establecimientos(
    *, texto: str = "", tipo: str = "", municipio: str = "", activo: str = "", estado: str = ""
):
    locales = Establecimiento.objects.all()
    if texto.strip():
        t = texto.strip()
        locales = locales.filter(
            Q(nombre__icontains=t) | Q(direccion__icontains=t) | Q(barrio__icontains=t)
        )
    if tipo in Establecimiento.Tipo.values:
        locales = locales.filter(tipo=tipo)
    if municipio:
        locales = locales.filter(municipio=municipio)
    if _si_no(activo) is not None:
        locales = locales.filter(activo=_si_no(activo))
    if estado in Establecimiento.Estado.values:
        locales = locales.filter(estado=estado)
    return locales.order_by("nombre")


def listar_usuarios(*, texto: str = "", rol: str = "", activo: str = ""):
    usuarios = Usuario.objects.all()
    if texto.strip():
        t = texto.strip()
        usuarios = usuarios.filter(Q(username__icontains=t) | Q(email__icontains=t))
    if rol in Usuario.Rol.values:
        usuarios = usuarios.filter(rol=rol)
    if _si_no(activo) is not None:
        usuarios = usuarios.filter(is_active=_si_no(activo))
    return usuarios.order_by("username")


def listar_auditoria(*, texto: str = "", entidad: str = "", accion: str = ""):
    registros = RegistroAuditoria.objects.select_related("actor")
    if texto.strip():
        t = texto.strip()
        registros = registros.filter(Q(objeto__icontains=t) | Q(actor__username__icontains=t))
    if entidad:
        registros = registros.filter(entidad=entidad)
    if accion in RegistroAuditoria.Accion.values:
        registros = registros.filter(accion=accion)
    return registros


# ---------- Opciones de los filtros ----------


def opciones_marcas() -> list[tuple[str, str]]:
    return [(str(pk), nombre) for pk, nombre in Marca.objects.values_list("pk", "nombre")]


def opciones_categorias() -> list[tuple[str, str]]:
    filas = Categoria.objects.order_by("nombre").values_list("pk", "nombre")
    return [(str(pk), nombre) for pk, nombre in filas]


def opciones_municipios() -> list[tuple[str, str]]:
    municipios = Establecimiento.objects.order_by("municipio").values_list("municipio", flat=True)
    return [(m, m) for m in municipios.distinct()]


def opciones_entidades() -> list[tuple[str, str]]:
    nombres = {
        "marca": "Marcas",
        "categoria": "Categorías",
        "producto": "Productos",
        "establecimiento": "Establecimientos",
        "usuario": "Usuarios",
    }
    return list(nombres.items())


def cifras() -> dict[str, int]:
    """Totales para la portada del panel (una consulta por modelo)."""
    return {
        "marcas": Marca.objects.count(),
        "categorias": Categoria.objects.count(),
        "productos": Producto.objects.count(),
        "establecimientos": Establecimiento.objects.count(),
        "usuarios": Usuario.objects.count(),
        "auditoria": RegistroAuditoria.objects.count(),
    }
