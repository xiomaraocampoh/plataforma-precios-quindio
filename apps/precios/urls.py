from django.urls import path

from . import views

app_name = "precios"

urlpatterns = [
    path("registrar/", views.registrar, name="registrar"),
    path("mis-aportes/", views.mis_aportes, name="mis_aportes"),
    path("reportes/<int:reporte_id>/sigue-igual/", views.sigue_igual, name="sigue_igual"),
]
