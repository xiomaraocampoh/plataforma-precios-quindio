"""Secciones del panel: una sola descripción por entidad para vistas, permisos, filtros y menú.

Los permisos son los de Django ("app.accion_modelo"): view para listar, add para crear, change
para editar y activar/desactivar, delete para eliminar. Se verifican en el servidor (views.py).
"""

from collections.abc import Callable
from dataclasses import dataclass, field

from django.urls import reverse

from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento

from . import forms, selectors
from .models import RegistroAuditoria

SI_NO = [("si", "Sí"), ("no", "No")]


@dataclass(frozen=True)
class Filtro:
    nombre: str
    etiqueta: str
    opciones: Callable[[], list[tuple[str, str]]]
    vacio: str = "Todos"


@dataclass(frozen=True)
class Seccion:
    slug: str
    entidad: str
    titulo: str
    singular: str
    femenino: bool
    app_label: str
    modelo: str
    formulario: type
    listar: Callable
    columnas: tuple[str, ...]
    descripcion: str
    filtros: tuple[Filtro, ...] = field(default_factory=tuple)
    formset: type | None = None
    busqueda: str = "Nombre"

    def permiso(self, accion: str) -> str:
        return f"{self.app_label}.{accion}_{self.modelo}"

    @property
    def articulo(self) -> str:
        return "la" if self.femenino else "el"

    @property
    def desactivalo(self) -> str:
        return "Desactívala" if self.femenino else "Desactívalo"

    @property
    def nuevo(self) -> str:
        return f"{'Nueva' if self.femenino else 'Nuevo'} {self.singular}"


SECCIONES = {
    s.slug: s
    for s in (
        Seccion(
            slug="marcas",
            entidad="marca",
            titulo="Marcas",
            singular="marca",
            femenino=True,
            app_label="catalogo",
            modelo="marca",
            formulario=forms.MarcaForm,
            listar=selectors.listar_marcas,
            columnas=("Marca", "Productos", "Estado"),
            descripcion="Una marca por nombre, sin importar tildes ni mayúsculas.",
            filtros=(
                Filtro(
                    "activa", "Estado", lambda: [("si", "Activas"), ("no", "Inactivas")], "Todas"
                ),
            ),
        ),
        Seccion(
            slug="categorias",
            entidad="categoria",
            titulo="Categorías",
            singular="categoría",
            femenino=True,
            app_label="catalogo",
            modelo="categoria",
            formulario=forms.CategoriaForm,
            listar=selectors.listar_categorias,
            columnas=("Categoría", "Departamento", "Perecedera", "Productos", "Estado"),
            descripcion="Agrupan productos y fijan cuánto dura un precio (perecederos: 3 días).",
            filtros=(
                Filtro(
                    "activa", "Estado", lambda: [("si", "Activas"), ("no", "Inactivas")], "Todas"
                ),
                Filtro("perecedera", "Perecedera", lambda: SI_NO, "Todas"),
            ),
        ),
        Seccion(
            slug="productos",
            entidad="producto",
            titulo="Productos",
            singular="producto",
            femenino=False,
            app_label="catalogo",
            modelo="producto",
            formulario=forms.ProductoForm,
            formset=forms.PresentacionesFormSet,
            listar=selectors.listar_productos,
            columnas=("Producto", "Categoría", "Presentaciones", "Estado"),
            descripcion="Productos con sus presentaciones (g, kg, ml, L, und) y código de barras.",
            busqueda="Nombre, marca o código de barras",
            filtros=(
                Filtro("marca", "Marca", selectors.opciones_marcas, "Todas"),
                Filtro("categoria", "Categoría", selectors.opciones_categorias, "Todas"),
                Filtro("activo", "Estado", lambda: [("si", "Activos"), ("no", "Inactivos")]),
            ),
        ),
        Seccion(
            slug="establecimientos",
            entidad="establecimiento",
            titulo="Establecimientos",
            singular="establecimiento",
            femenino=False,
            app_label="establecimientos",
            modelo="establecimiento",
            formulario=forms.EstablecimientoForm,
            listar=selectors.listar_establecimientos,
            columnas=("Establecimiento", "Ubicación", "Estado"),
            descripcion="Tiendas, minimercados y supermercados del directorio.",
            busqueda="Nombre, dirección o barrio",
            filtros=(
                Filtro("tipo", "Tipo", lambda: list(Establecimiento.Tipo.choices)),
                Filtro("municipio", "Municipio", selectors.opciones_municipios),
                Filtro("estado", "Moderación", lambda: list(Establecimiento.Estado.choices)),
                Filtro("activo", "Estado", lambda: [("si", "Activos"), ("no", "Inactivos")]),
            ),
        ),
    )
}

FILTROS_USUARIOS = (
    Filtro("rol", "Rol", lambda: list(Usuario.Rol.choices)),
    Filtro("activo", "Estado", lambda: [("si", "Activas"), ("no", "Suspendidas")], "Todas"),
)
FILTROS_AUDITORIA = (
    Filtro("entidad", "Sección", selectors.opciones_entidades, "Todas"),
    Filtro("accion", "Acción", lambda: list(RegistroAuditoria.Accion.choices), "Todas"),
)
PERMISO_USUARIOS = "cuentas.view_usuario"
PERMISO_GESTIONAR_CUENTAS = "cuentas.gestionar_cuentas"
PERMISO_AUDITORIA = "administracion.view_registroauditoria"


def accesos(usuario) -> list[dict]:
    """Secciones que el usuario puede ver, para el menú y la portada del panel."""
    if not (usuario and usuario.is_authenticated and usuario.is_active):
        return []
    lista = [
        {
            "slug": s.slug,
            "titulo": s.titulo,
            "descripcion": s.descripcion,
            "url": reverse("panel:lista", args=[s.slug]),
        }
        for s in SECCIONES.values()
        if usuario.has_perm(s.permiso("view"))
    ]
    if usuario.has_perm(PERMISO_USUARIOS):
        lista.append(
            {
                "slug": "usuarios",
                "titulo": "Usuarios",
                "descripcion": "Roles y estado de las cuentas.",
                "url": reverse("panel:usuarios"),
            }
        )
    if usuario.has_perm(PERMISO_AUDITORIA):
        lista.append(
            {
                "slug": "auditoria",
                "titulo": "Auditoría",
                "descripcion": "Quién hizo qué y cuándo en el panel.",
                "url": reverse("panel:auditoria"),
            }
        )
    return lista
