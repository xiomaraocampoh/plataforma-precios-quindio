from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods

from . import services
from .forms import RegistroForm


class IngresarView(LoginView):
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
