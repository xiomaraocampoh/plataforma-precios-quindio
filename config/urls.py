from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.views import healthz

api_v1 = [
    path("precios/", include("apps.precios.api.urls")),
    path("comparacion/", include("apps.comparacion.api.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
    path("healthz/", healthz, name="healthz"),
    path("precios/", include("apps.precios.urls")),
    path("", include("apps.comparacion.urls")),
]
