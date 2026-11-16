from django.urls import path

from . import views

app_name = "correos"

urlpatterns = [
    path("vista-previa/", views.indice, name="indice"),
    path("vista-previa/<str:tipo>/", views.vista_previa, name="vista_previa"),
]
