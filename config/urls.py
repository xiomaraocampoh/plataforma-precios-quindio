from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.notificaciones.interno import procesar_correos
from core.views import healthz

api_v1 = [
    path("precios/", include("apps.precios.api.urls")),
    path("comparacion/", include("apps.comparacion.api.urls")),
    path("catalogo/", include("apps.catalogo.api.urls")),
    path("establecimientos/", include("apps.establecimientos.api.urls")),
    path("moderacion/", include("apps.moderacion.api.urls")),
]

urlpatterns = [
    # El ingreso a /admin/ pasa por el de la plataforma: así también exige el segundo factor
    path(
        "admin/login/",
        RedirectView.as_view(pattern_name="cuentas:ingresar", query_string=True),
    ),
    path("admin/", admin.site.urls),  # se conserva para el superusuario
    path("panel/correos/", include("apps.notificaciones.urls")),  # vista previa (solo staff)
    path("panel/", include("apps.administracion.urls")),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
    path("healthz/", healthz, name="healthz"),
    path("interno/correos/procesar/", procesar_correos, name="procesar_correos"),
    path("cuentas/", include("apps.cuentas.urls")),
    path("precios/", include("apps.precios.urls")),
    path("catalogo/", include("apps.catalogo.urls")),
    path("establecimientos/", include("apps.establecimientos.urls")),
    path("moderacion/", include("apps.moderacion.urls")),
    path("", include("apps.comparacion.urls")),
]
