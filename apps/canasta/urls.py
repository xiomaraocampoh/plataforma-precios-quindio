from django.urls import path

from . import views

app_name = "canasta"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("buscar/", views.buscar, name="buscar"),
    path("agregar/", views.agregar, name="agregar"),
    path("cambiar/<int:producto_id>/", views.cambiar, name="cambiar"),
    path("quitar/<int:producto_id>/", views.quitar, name="quitar"),
    path("vaciar/", views.vaciar, name="vaciar"),
    path("resultado/", views.resultado, name="resultado"),
]
