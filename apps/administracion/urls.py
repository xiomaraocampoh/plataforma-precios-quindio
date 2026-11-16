from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/<int:pk>/", views.usuario, name="usuario"),
    path("usuarios/<int:pk>/estado/", views.usuario_estado, name="usuario_estado"),
    path("auditoria/", views.auditoria, name="auditoria"),
    path("<slug:seccion>/", views.lista, name="lista"),
    path("<slug:seccion>/nuevo/", views.nuevo, name="nuevo"),
    path("<slug:seccion>/<int:pk>/", views.editar, name="editar"),
    path("<slug:seccion>/<int:pk>/estado/", views.estado, name="estado"),
    path("<slug:seccion>/<int:pk>/eliminar/", views.eliminar, name="eliminar"),
]
