from django.urls import path

from .views import EstablecimientosAPI, SugerenciaEstablecimientoAPI

urlpatterns = [
    path("", EstablecimientosAPI.as_view(), name="api-establecimientos"),
    path("sugerencias/", SugerenciaEstablecimientoAPI.as_view(), name="api-sugerencias"),
]
