from django.contrib import admin

from core.admin_acciones import accion_de_moderacion

from . import services
from .models import DecisionModeracion, Denuncia


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ("id", "reporte", "motivo", "estado", "creado_en", "resuelto_por")
    list_filter = ("estado", "motivo")
    raw_id_fields = ("reporte", "denunciante", "resuelto_por")
    readonly_fields = ("resuelto_por", "resuelto_en")
    actions = [
        accion_de_moderacion(
            "Aceptar y retirar el precio",
            lambda m, d: services.resolver_denuncia(moderador=m, denuncia_id=d.pk, aceptar=True),
        ),
        accion_de_moderacion(
            "Descartar denuncias",
            lambda m, d: services.resolver_denuncia(moderador=m, denuncia_id=d.pk, aceptar=False),
        ),
    ]


@admin.register(DecisionModeracion)
class DecisionModeracionAdmin(admin.ModelAdmin):
    """Bitácora de solo lectura (M-14): nadie la edita ni la borra desde el admin."""

    list_display = ("creado_en", "moderador", "accion", "objeto_tipo", "objeto_id", "motivo")
    list_filter = ("accion", "objeto_tipo")
    date_hierarchy = "creado_en"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
