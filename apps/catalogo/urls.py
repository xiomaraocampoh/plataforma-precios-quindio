from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("solicitar/", views.solicitar, name="solicitar"),
    path("similares/", views.similares, name="similares"),
]
