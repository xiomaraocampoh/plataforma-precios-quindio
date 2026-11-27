from django.urls import path

from . import views

app_name = "comercios"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("perfil/", views.crear_perfil, name="crear_perfil"),
    path("precios/", views.publicar_precio, name="publicar_precio"),
    path("precios/<int:precio_id>/retirar/", views.retirar_precio, name="retirar_precio"),
    path("precios/confirmar/", views.confirmar_vigencia, name="confirmar_vigencia"),
    path("promociones/", views.crear_promocion, name="crear_promocion"),
    path(
        "promociones/<int:promocion_id>/terminar/",
        views.finalizar_promocion,
        name="finalizar_promocion",
    ),
    path("correcciones/", views.solicitar_correccion, name="solicitar_correccion"),
    path("verificacion/", views.verificacion, name="verificacion"),
    path("verificacion/perfil/<int:perfil_id>/", views.decidir_perfil, name="decidir_perfil"),
    path(
        "verificacion/perfil/<int:perfil_id>/documento/<str:tipo>/",
        views.documento_perfil,
        name="documento_perfil",
    ),
    path(
        "verificacion/correccion/<int:solicitud_id>/",
        views.decidir_correccion,
        name="decidir_correccion",
    ),
]
