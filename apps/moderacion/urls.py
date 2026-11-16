from django.urls import path

from . import views

app_name = "moderacion"

urlpatterns = [
    path("", views.bandeja, name="bandeja"),
    path("decidir/", views.decidir, name="decidir"),
    path("denunciar/<int:reporte_id>/", views.denunciar, name="denunciar"),
]
