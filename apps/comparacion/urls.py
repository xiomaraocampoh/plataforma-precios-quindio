from django.urls import path

from . import views

app_name = "comparacion"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("sugerencias/", views.sugerencias, name="sugerencias"),
    path("escanear/", views.escanear, name="escanear"),
    path("buscar-por-foto/", views.buscar_por_foto, name="buscar_por_foto"),
    path("escanear/fotograma/", views.escanear_fotograma, name="escanear_fotograma"),
    path("productos/", views.productos, name="productos"),
    path("productos/<int:producto_id>/", views.comparar, name="comparar"),
    path("tiendas/<int:establecimiento_id>/", views.establecimiento, name="establecimiento"),
]
