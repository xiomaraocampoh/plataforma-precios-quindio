from django.urls import path

from .views import RegistrarReporteAPI

urlpatterns = [
    path("reportes/", RegistrarReporteAPI.as_view(), name="api-registrar-reporte"),
]
