from django.contrib import admin

from apps.moderacion import services as moderacion
from core.admin_acciones import accion_de_moderacion

from .models import Establecimiento


@admin.register(Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "barrio", "municipio", "estado", "activo")
    list_filter = ("estado", "tipo", "municipio", "activo")
    search_fields = ("nombre", "barrio", "direccion")
    readonly_fields = ("sugerido_por", "revisado_por", "revisado_en")
    actions = [
        accion_de_moderacion(
            "Aprobar establecimientos sugeridos",
            lambda m, e: moderacion.decidir_establecimiento(
                moderador=m, establecimiento_id=e.pk, aprobar=True
            ),
        ),
        accion_de_moderacion(
            "Rechazar establecimientos sugeridos",
            lambda m, e: moderacion.decidir_establecimiento(
                moderador=m, establecimiento_id=e.pk, aprobar=False
            ),
        ),
    ]
