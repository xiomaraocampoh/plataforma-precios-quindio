from django.urls import path

from . import views

app_name = "precios"

urlpatterns = [
    path("registrar/", views.registrar, name="registrar"),
]
