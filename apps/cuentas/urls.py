from django.contrib.auth import views as auth
from django.contrib.auth.views import LogoutView
from django.urls import path, reverse_lazy

from . import views

app_name = "cuentas"

urlpatterns = [
    path("ingresar/", views.IngresarView.as_view(), name="ingresar"),
    path("salir/", LogoutView.as_view(), name="salir"),
    path("registro/", views.registro, name="registro"),
    path("mis-datos/", views.mis_datos, name="mis_datos"),
    path("mis-datos/suprimir/", views.suprimir, name="suprimir"),
    # RF-02: recuperación de contraseña (vistas de Django; enlace de un solo uso)
    path(
        "contrasena/recuperar/",
        auth.PasswordResetView.as_view(
            template_name="cuentas/recuperar.html",
            email_template_name="cuentas/correo_recuperar.txt",
            subject_template_name="cuentas/asunto_recuperar.txt",
            success_url=reverse_lazy("cuentas:recuperar_enviado"),
        ),
        name="recuperar",
    ),
    path(
        "contrasena/recuperar/enviado/",
        auth.PasswordResetDoneView.as_view(template_name="cuentas/recuperar_enviado.html"),
        name="recuperar_enviado",
    ),
    path(
        "contrasena/restablecer/<uidb64>/<token>/",
        auth.PasswordResetConfirmView.as_view(
            template_name="cuentas/restablecer.html",
            success_url=reverse_lazy("cuentas:restablecer_listo"),
        ),
        name="restablecer",
    ),
    path(
        "contrasena/restablecer/listo/",
        auth.PasswordResetCompleteView.as_view(template_name="cuentas/restablecer_listo.html"),
        name="restablecer_listo",
    ),
]
