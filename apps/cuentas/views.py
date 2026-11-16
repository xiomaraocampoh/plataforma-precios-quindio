from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from apps.precios.selectors import contar_aportes

from . import services
from .forms import DatosForm, IngresarForm, RegistroForm, SuprimirCuentaForm


class IngresarView(LoginView):
    authentication_form = IngresarForm
    template_name = "cuentas/ingresar.html"
    redirect_authenticated_user = True


@require_http_methods(["GET", "POST"])
def registro(request):
    if request.user.is_authenticated:
        return redirect("comparacion:inicio")
    siguiente = request.POST.get("next") or request.GET.get("next") or ""
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        usuario = services.registrar_usuario(
            username=d["username"], email=d["email"], password=d["password1"]
        )
        login(request, usuario)
        messages.success(request, "Tu cuenta quedó creada. Ya puedes registrar precios.")
        seguro = url_has_allowed_host_and_scheme(siguiente, allowed_hosts={request.get_host()})
        return redirect(siguiente if seguro and siguiente else "precios:registrar")
    return render(request, "cuentas/registro.html", {"form": form, "next": siguiente})


@login_required
@require_http_methods(["GET", "POST"])
def mis_datos(request):
    """RF-03: ver y actualizar los datos personales."""
    usuario = request.user
    form = DatosForm(
        request.POST or None,
        usuario=usuario,
        initial={"username": usuario.username, "email": usuario.email},
    )
    if request.method == "POST" and form.is_valid():
        services.actualizar_datos(
            usuario=usuario,
            username=form.cleaned_data["username"],
            email=form.cleaned_data["email"],
        )
        messages.success(request, "Tus datos quedaron actualizados.")
        return redirect("cuentas:mis_datos")
    contexto = {"form": form, "aportes": contar_aportes(usuario)}
    return render(request, "cuentas/mis_datos.html", contexto)


@login_required
@require_http_methods(["GET", "POST"])
def suprimir(request):
    """RF-03: supresión de la cuenta; los aportes se conservan anonimizados."""
    form = SuprimirCuentaForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        services.suprimir_cuenta(usuario=request.user)
        logout(request)
        messages.success(
            request, "Tu cuenta fue suprimida. Tus precios siguen publicados sin tu identidad."
        )
        return redirect("comparacion:inicio")
    return render(request, "cuentas/suprimir.html", {"form": form})
