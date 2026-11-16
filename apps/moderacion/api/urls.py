from django.urls import path

from .views import DenunciasAPI, ReporteEnRevisionAPI, ReportesEnRevisionAPI

urlpatterns = [
    path("denuncias/", DenunciasAPI.as_view(), name="api-denuncias"),
    path("reportes-en-revision/", ReportesEnRevisionAPI.as_view(), name="api-en-revision"),
    path(
        "reportes-en-revision/<int:pk>/",
        ReporteEnRevisionAPI.as_view(),
        name="api-en-revision-detalle",
    ),
]
