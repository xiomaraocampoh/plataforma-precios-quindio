from django.urls import path

from . import views

app_name = "establecimientos"

urlpatterns = [
    path("", views.directorio, name="directorio"),
    path("sugerir/", views.sugerir, name="sugerir"),
]
