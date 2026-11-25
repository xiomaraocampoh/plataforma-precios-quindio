from django.urls import path

from . import views

urlpatterns = [
    path("perfil/", views.PerfilAPI.as_view(), name="api-comercios-perfil"),
    path("precios/", views.PreciosOficialesAPI.as_view(), name="api-comercios-precios"),
    path(
        "precios/confirmar/",
        views.ConfirmarVigenciaAPI.as_view(),
        name="api-comercios-confirmar",
    ),
    path("promociones/", views.PromocionesAPI.as_view(), name="api-comercios-promociones"),
    path(
        "promociones/<int:promocion_id>/terminar/",
        views.TerminarPromocionAPI.as_view(),
        name="api-comercios-terminar-promocion",
    ),
]
