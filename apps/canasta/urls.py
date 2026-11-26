from django.urls import path

from . import views

app_name = "canasta"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("enviar/", views.enviar, name="enviar"),
]
