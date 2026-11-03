from django.contrib import admin

from .models import ReportePrecio


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
