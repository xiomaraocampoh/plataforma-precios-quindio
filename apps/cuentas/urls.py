from django.contrib.auth import views as auth
from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("ingresar/", views.IngresarView.as_view(), name="ingresar"),
    # RF-27: segundo paso del ingreso (la sesión aún no está abierta)
    path("ingresar/verificar/", views.verificar, name="ingresar_verificar"),
    path("ingresar/codigo/", views.reenviar_codigo, name="ingresar_codigo"),
    path("ingresar/configurar/", views.configurar_al_ingresar, name="ingresar_configurar"),
    path("salir/", LogoutView.as_view(), name="salir"),
    path("registro/", views.registro, name="registro"),
    # Ley 1581: política de tratamiento de datos, pública (se lee antes de autorizar)
    path("politica-de-datos/", views.politica_datos, name="politica_datos"),
    path("mis-datos/", views.mis_datos, name="mis_datos"),
    path("mis-datos/suprimir/", views.suprimir, name="suprimir"),
    path("mis-datos/preferencias/", views.preferencias, name="preferencias"),
    # RF-27: verificación en dos pasos y contraseña
    path("seguridad/", views.seguridad, name="seguridad"),
    path("seguridad/app/", views.configurar_app, name="configurar_app"),
    path("seguridad/contrasena/", views.CambiarContrasenaView.as_view(), name="contrasena"),
    # RF-24: verificación del correo
    path("verificar-correo/reenviar/", views.reenviar_verificacion, name="reenviar_verificacion"),
    path("verificar-correo/<str:token>/", views.verificar_correo, name="verificar_correo"),
    # RF-25: «no fui yo» tras un cambio de contraseña
    path("no-fui-yo/<str:token>/", views.no_fui_yo, name="no_fui_yo"),
    # Ley 1581: baja de los correos informativos (enlace del pie y List-Unsubscribe)
    path("correo/baja/<str:token>/", views.baja, name="baja"),
    # RF-02: recuperación de contraseña (enlace de un solo uso, con la cola de correo)
    path("contrasena/recuperar/", views.RecuperarView.as_view(), name="recuperar"),
    path(
        "contrasena/recuperar/enviado/",
        auth.PasswordResetDoneView.as_view(template_name="cuentas/recuperar_enviado.html"),
        name="recuperar_enviado",
    ),
    path(
        "contrasena/restablecer/<uidb64>/<token>/",
        views.RestablecerView.as_view(),
        name="restablecer",
    ),
    path(
        "contrasena/restablecer/listo/",
        auth.PasswordResetCompleteView.as_view(template_name="cuentas/restablecer_listo.html"),
        name="restablecer_listo",
    ),
]
