"""Vistas del panel (/panel/). HTMX para listados; sin JS todo funciona con enlaces y formularios.

Cada vista verifica el permiso en el servidor ANTES de leer o escribir (403 si falta). Ocultar
botones en la plantilla es solo comodidad. Las escrituras pasan por services (con auditoría).
"""

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from core.errores import EnUsoError

from . import selectors, services
from .forms import RolForm
from .secciones import (
    FILTROS_AUDITORIA,
    FILTROS_USUARIOS,
    PERMISO_AUDITORIA,
    PERMISO_GESTIONAR_CUENTAS,
    PERMISO_USUARIOS,
    SECCIONES,
    accesos,
)

POR_PAGINA = 20


def _exigir(usuario, permiso: str) -> None:
    if not usuario.has_perm(permiso):
        raise PermissionDenied("No tienes permiso para esta sección del panel.")


def _seccion(slug: str):
    seccion = SECCIONES.get(slug)
    if seccion is None:
        raise Http404("Sección inexistente.")
    return seccion


def _objeto(seccion, pk: int):
    objeto = selectors.obtener(seccion.entidad, pk)
    if objeto is None:
        raise Http404(f"No existe {seccion.articulo} {seccion.singular}.")
    return objeto


def _mensajes_de(error: ValidationError) -> str:
    return " ".join(error.messages)


def _listado(request, *, consulta, filtros, plantilla, parcial, contexto):
    """Página completa o, con HTMX, solo el fragmento de resultados (mismo contexto)."""
    texto = request.GET.get("q", "").strip()
    valores = {f.nombre: request.GET.get(f.nombre, "") for f in filtros}
    pagina = Paginator(consulta(texto=texto, **valores), POR_PAGINA).get_page(
        request.GET.get("pagina")
    )
    parametros = {k: v for k, v in request.GET.items() if k != "pagina" and v}
    contexto.update(
        {
            "pagina": pagina,
            "q": texto,
            "filtros": [(f, f.opciones(), valores[f.nombre]) for f in filtros],
            "hay_filtros": bool(parametros),
            "consulta": urlencode(parametros),
            "accesos": accesos(request.user),
        }
    )
    return render(request, parcial if request.htmx else plantilla, contexto)


# ---------- Portada ----------


@login_required
@require_GET
def inicio(request):
    tarjetas = accesos(request.user)
    if not tarjetas:
        raise PermissionDenied("Tu cuenta no tiene acceso al panel.")
    cifras = selectors.cifras()
    for tarjeta in tarjetas:
        tarjeta["total"] = cifras.get(tarjeta["slug"])
    return render(request, "administracion/inicio.html", {"accesos": tarjetas})


# ---------- Catálogo y establecimientos (genérico por sección) ----------


@login_required
@require_GET
def lista(request, seccion: str):
    s = _seccion(seccion)
    _exigir(request.user, s.permiso("view"))
    permisos = {a: request.user.has_perm(s.permiso(a)) for a in ("add", "change", "delete")}
    return _listado(
        request,
        consulta=s.listar,
        filtros=s.filtros,
        plantilla="administracion/lista.html",
        parcial="administracion/partials/_resultados.html",
        contexto={"seccion": s, "puede": permisos},
    )


def _formulario(request, s, objeto=None):
    form = s.formulario(request.POST or None, instance=objeto)
    formset = (
        s.formset(request.POST or None, instance=objeto, prefix="presentaciones")
        if s.formset
        else None
    )
    if request.method == "POST" and form.is_valid() and (formset is None or formset.is_valid()):
        try:
            guardado = services.guardar(
                actor=request.user, entidad=s.entidad, form=form, formset=formset
            )
        except EnUsoError as exc:
            form.add_error(None, str(exc))
        except ValidationError as exc:
            form.add_error(None, _mensajes_de(exc))
        else:
            verbo = "guardó" if objeto else "creó"
            messages.success(request, f"Se {verbo} {s.articulo} {s.singular} «{guardado}».")
            return redirect("panel:lista", s.slug)
    contexto = {
        "seccion": s,
        "form": form,
        "formset": formset,
        "objeto": objeto,
        "accesos": accesos(request.user),
    }
    return render(request, "administracion/formulario.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def nuevo(request, seccion: str):
    s = _seccion(seccion)
    _exigir(request.user, s.permiso("add"))
    return _formulario(request, s)


@login_required
@require_http_methods(["GET", "POST"])
def editar(request, seccion: str, pk: int):
    s = _seccion(seccion)
    _exigir(request.user, s.permiso("change"))
    return _formulario(request, s, _objeto(s, pk))


@login_required
@require_http_methods(["GET", "POST"])
def estado(request, seccion: str, pk: int):
    """GET: pide confirmación. POST: activa o desactiva (no borra)."""
    s = _seccion(seccion)
    _exigir(request.user, s.permiso("change"))
    objeto = _objeto(s, pk)
    activo = getattr(objeto, "activa", getattr(objeto, "activo", True))
    if request.method == "POST":
        try:
            services.cambiar_estado(actor=request.user, entidad=s.entidad, objeto=objeto)
        except ValidationError as exc:
            messages.error(request, _mensajes_de(exc))
        else:
            hecho = "desactivó" if activo else "activó"
            messages.success(request, f"Se {hecho} {s.articulo} {s.singular} «{objeto}».")
        return redirect("panel:lista", s.slug)
    verbo = "Desactivar" if activo else "Activar"
    contexto = {
        "seccion": s,
        "objeto": objeto,
        "accesos": accesos(request.user),
        "titulo": f"¿{verbo} {s.articulo} {s.singular} «{objeto}»?",
        "explicacion": (
            "Dejará de ofrecerse en búsquedas, filtros y en el registro de precios. "
            "No se borra nada: los reportes y el historial se conservan y puedes reactivarlo."
            if activo
            else "Volverá a ofrecerse al público."
        ),
        "boton": verbo,
        "peligro": activo,
    }
    return render(request, "administracion/confirmar.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def eliminar(request, seccion: str, pk: int):
    """GET: pide confirmación (o explica por qué no se puede). POST: elimina si nada lo usa."""
    s = _seccion(seccion)
    _exigir(request.user, s.permiso("delete"))
    objeto = _objeto(s, pk)
    no_se_puede = (
        f"No se puede eliminar {s.articulo} {s.singular} «{objeto}»: tiene reportes u otros "
        f"registros asociados. {s.desactivalo} para retirarl{'a' if s.femenino else 'o'} "
        "sin perder el historial."
    )
    if request.method == "POST":
        try:
            services.eliminar(actor=request.user, entidad=s.entidad, objeto=objeto)
        except EnUsoError:
            messages.error(request, no_se_puede)
        else:
            messages.success(request, f"Se eliminó {s.articulo} {s.singular} «{objeto}».")
        return redirect("panel:lista", s.slug)
    puede = selectors.puede_eliminarse(objeto)
    contexto = {
        "seccion": s,
        "objeto": objeto,
        "accesos": accesos(request.user),
        "titulo": f"¿Eliminar {s.articulo} {s.singular} «{objeto}»?",
        "explicacion": "Se borra de forma definitiva. Esta acción no se puede deshacer."
        if puede
        else no_se_puede,
        "boton": "Eliminar" if puede else "",
        "peligro": True,
    }
    return render(request, "administracion/confirmar.html", contexto)


# ---------- Usuarios ----------


@login_required
@require_GET
def usuarios(request):
    _exigir(request.user, PERMISO_USUARIOS)
    return _listado(
        request,
        consulta=selectors.listar_usuarios,
        filtros=FILTROS_USUARIOS,
        plantilla="administracion/usuarios.html",
        parcial="administracion/partials/_usuarios.html",
        contexto={
            "puede_gestionar": request.user.has_perm(PERMISO_GESTIONAR_CUENTAS),
            "activo": "usuarios",
        },
    )


def _usuario(pk: int):
    usuario = selectors.obtener_usuario(pk)
    if usuario is None:
        raise Http404("No existe la cuenta.")
    return usuario


@login_required
@require_http_methods(["GET", "POST"])
def usuario(request, pk: int):
    """Ficha de la cuenta. GET con permiso de ver; POST (asignar rol) con gestionar_cuentas."""
    _exigir(
        request.user, PERMISO_GESTIONAR_CUENTAS if request.method == "POST" else PERMISO_USUARIOS
    )
    cuenta = _usuario(pk)
    form = RolForm(request.POST or None, initial={"rol": cuenta.rol})
    if request.method == "POST" and form.is_valid():
        try:
            services.asignar_rol(
                actor=request.user, usuario_id=cuenta.pk, rol=form.cleaned_data["rol"]
            )
        except ValidationError as exc:
            form.add_error(None, _mensajes_de(exc))
        else:
            messages.success(request, f"Se actualizó el rol de «{cuenta}».")
            return redirect("panel:usuarios")
    contexto = {
        "cuenta": cuenta,
        "form": form,
        "accesos": accesos(request.user),
        "activo": "usuarios",
        "puede_gestionar": request.user.has_perm(PERMISO_GESTIONAR_CUENTAS),
        "es_propia": cuenta.pk == request.user.pk,
        "protegida": cuenta.is_superuser and not request.user.is_superuser,
        "grupos": list(cuenta.groups.order_by("name").values_list("name", flat=True)),
    }
    return render(request, "administracion/usuario.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def usuario_estado(request, pk: int):
    """GET: confirmación. POST: suspende o reactiva (nunca la propia ni un superusuario)."""
    _exigir(request.user, PERMISO_GESTIONAR_CUENTAS)
    cuenta = _usuario(pk)
    if request.method == "POST":
        try:
            services.alternar_cuenta(actor=request.user, usuario_id=cuenta.pk)
        except ValidationError as exc:
            messages.error(request, _mensajes_de(exc))
        else:
            hecho = "suspendió" if cuenta.is_active else "reactivó"
            messages.success(request, f"Se {hecho} la cuenta «{cuenta}».")
        return redirect("panel:usuarios")
    verbo = "Suspender" if cuenta.is_active else "Reactivar"
    contexto = {
        "objeto": cuenta,
        "accesos": accesos(request.user),
        "activo": "usuarios",
        "titulo": f"¿{verbo} la cuenta «{cuenta}»?",
        "explicacion": (
            "No podrá ingresar ni registrar precios. Sus aportes se conservan y son auditables."
            if cuenta.is_active
            else "Podrá volver a ingresar con su contraseña."
        ),
        "boton": verbo,
        "peligro": cuenta.is_active,
        "volver": "panel:usuarios",
    }
    return render(request, "administracion/confirmar.html", contexto)


# ---------- Auditoría ----------


@login_required
@require_GET
def auditoria(request):
    _exigir(request.user, PERMISO_AUDITORIA)
    return _listado(
        request,
        consulta=selectors.listar_auditoria,
        filtros=FILTROS_AUDITORIA,
        plantilla="administracion/auditoria.html",
        parcial="administracion/partials/_auditoria.html",
        contexto={"activo": "auditoria"},
    )
