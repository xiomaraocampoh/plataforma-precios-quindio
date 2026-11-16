from django.contrib import admin

from apps.moderacion import services as moderacion
from core.admin_acciones import accion_de_moderacion

from .models import ConfirmacionPrecio, ReportePrecio


@admin.register(ReportePrecio)
class ReportePrecioAdmin(admin.ModelAdmin):
    list_display = (
        "presentacion",
        "establecimiento",
        "precio",
        "fuente",
        "estado",
        "fecha_observacion",
    )
    list_filter = ("estado", "fuente")
    raw_id_fields = ("presentacion", "establecimiento", "autor")
    date_hierarchy = "fecha_observacion"
    list_select_related = ("presentacion__producto", "establecimiento")
    actions = [
        accion_de_moderacion(
            "Publicar reportes en revisión",
            lambda m, r: moderacion.decidir_reporte(moderador=m, reporte_id=r.pk, aprobar=True),
        ),
        accion_de_moderacion(
            "Rechazar reportes en revisión",
            lambda m, r: moderacion.decidir_reporte(moderador=m, reporte_id=r.pk, aprobar=False),
        ),
    ]


@admin.register(ConfirmacionPrecio)
class ConfirmacionPrecioAdmin(admin.ModelAdmin):
    list_display = ("reporte", "fecha", "creado_en")
    raw_id_fields = ("reporte", "usuario")
    date_hierarchy = "creado_en"
