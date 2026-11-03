from django.urls import path

from .views import ComparacionAPI

urlpatterns = [
    path("<int:producto_id>/", ComparacionAPI.as_view(), name="api-comparacion"),
]
