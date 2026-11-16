from django.urls import path

from . import views

app_name = "comparacion"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("sugerencias/", views.sugerencias, name="sugerencias"),
    path("escanear/", views.escanear, name="escanear"),
    path("productos/", views.productos, name="productos"),
    path("productos/<int:producto_id>/", views.comparar, name="comparar"),
]
