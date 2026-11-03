from django.urls import path

from . import views

app_name = "comparacion"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("sugerencias/", views.sugerencias, name="sugerencias"),
    path("productos/<int:producto_id>/", views.comparar, name="comparar"),
]
