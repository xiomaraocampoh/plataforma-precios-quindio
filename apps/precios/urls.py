from django.urls import path

from . import views

app_name = "precios"

urlpatterns = [
    path("registrar/", views.registrar, name="registrar"),
    path("mis-aportes/", views.mis_aportes, name="mis_aportes"),
]
