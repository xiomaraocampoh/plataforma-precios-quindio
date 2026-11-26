"""Casos de uso del panel (capa de aplicación).

Cada acción llama al servicio del módulo dueño del dato (nunca escribe en el ORM de otro módulo)
y deja su registro de auditoría en la MISMA transacción: si la acción falla, no queda registro;
si el registro falla, la acción se deshace (M-14).
"""

from django.db import transaction

from apps.catalogo import services as catalogo
from apps.catalogo.domain.normalizacion import formatear_cantidad
from apps.cuentas import services as cuentas
from apps.establecimientos import services as establecimientos

from .. import selectors
from ..domain.auditoria import diferencias
from ..models import RegistroAuditoria

Accion = RegistroAuditoria.Accion

# Lo que el panel puede cambiar de cada entidad y, por eso, lo que se audita
CAMPOS = {
    "marca": ("nombre", "activa"),
    "categoria": ("nombre", "perecedera", "activa"),
    "producto": ("nombre", "marca", "categoria", "descripcion", "activo"),
    "establecimiento": (
        "nombre",
        "tipo",
        "direccion",
        "barrio",
        "municipio",
        "latitud",
        "longitud",
        "activo",
    ),
}
_DUENO = {
    "marca": catalogo,
    "categoria": catalogo,
    "producto": catalogo,
    "establecimiento": establecimientos,
}


def _campo_activo(objeto) -> str:
    return "activa" if hasattr(objeto, "activa") else "activo"


def instantanea(entidad: str, objeto) -> dict:
    datos = {campo: getattr(objeto, campo) for campo in CAMPOS[entidad]}
    if entidad == "producto":
        datos["foto"] = objeto.foto_version or "sin foto"  # versión, no los bytes
        datos["presentaciones"] = sorted(
            f"{formatear_cantidad(p.cantidad)} {p.unidad}"
            + (f" · {p.codigo_barras}" if p.codigo_barras else "")
            + ("" if p.activa else " (inactiva)")
            for p in objeto.presentaciones.all()
        )
    return datos


def _registrar(actor, accion: str, entidad: str, objeto_id: int, texto: str, cambios: dict):
    return RegistroAuditoria.objects.create(
        actor=actor,
        accion=accion,
        entidad=entidad,
        objeto_id=objeto_id,
        objeto=texto[:200],
        cambios=cambios,
    )


@transaction.atomic
def guardar(*, actor, entidad: str, form, formset=None):
    """Crea o edita desde un formulario ya validado y audita lo que cambió."""
    original = form.instance
    antes = {}
    if original.pk is not None:
        antes = instantanea(entidad, type(original)._default_manager.get(pk=original.pk))
    if entidad == "establecimiento":
        objeto = establecimientos.guardar_formulario(form)
    else:
        objeto = catalogo.guardar_formulario(form, formset)
    cambios = diferencias(antes, instantanea(entidad, objeto))
    if not antes:
        _registrar(actor, Accion.CREAR, entidad, objeto.pk, str(objeto), cambios)
    elif cambios:
        _registrar(actor, Accion.EDITAR, entidad, objeto.pk, str(objeto), cambios)
    return objeto


@transaction.atomic
def cambiar_estado(*, actor, entidad: str, objeto):
    """Alterna activo/inactivo. Nunca borra: lo inactivo deja de ofrecerse al público."""
    campo = _campo_activo(objeto)
    actual = getattr(objeto, campo)
    _DUENO[entidad].cambiar_estado(objeto, activo=not actual)
    accion = Accion.DESACTIVAR if actual else Accion.ACTIVAR
    _registrar(actor, accion, entidad, objeto.pk, str(objeto), {campo: [actual, not actual]})
    return objeto


@transaction.atomic
def eliminar(*, actor, entidad: str, objeto) -> None:
    """Borra solo lo que nada referencia; si tiene reportes u otros registros: EnUsoError."""
    pk, texto, datos = objeto.pk, str(objeto), instantanea(entidad, objeto)
    _DUENO[entidad].eliminar(objeto)
    _registrar(actor, Accion.ELIMINAR, entidad, pk, texto, diferencias(datos, {}))


@transaction.atomic
def asignar_rol(*, actor, usuario_id: int, rol: str):
    anterior = selectors.obtener_usuario(usuario_id).rol
    usuario = cuentas.asignar_rol(actor=actor, usuario_id=usuario_id, rol=rol)
    if anterior != usuario.rol:
        cambios = {"rol": [anterior, usuario.rol]}
        _registrar(actor, Accion.ASIGNAR_ROL, "usuario", usuario.pk, usuario.username, cambios)
    return usuario


@transaction.atomic
def alternar_cuenta(*, actor, usuario_id: int):
    """Suspende una cuenta activa o reactiva una suspendida."""
    activa = selectors.obtener_usuario(usuario_id).is_active
    usuario = cuentas.cambiar_estado_cuenta(actor=actor, usuario_id=usuario_id, activa=not activa)
    accion = Accion.DESACTIVAR if activa else Accion.ACTIVAR
    cambios = {"is_active": [activa, not activa]}
    _registrar(actor, accion, "usuario", usuario.pk, usuario.username, cambios)
    return usuario
