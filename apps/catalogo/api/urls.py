from django.urls import path

from .views import ProductoAPI, ProductosAPI

urlpatterns = [
    path("productos/", ProductosAPI.as_view(), name="api-productos"),
    path("productos/<int:pk>/", ProductoAPI.as_view(), name="api-producto"),
]
