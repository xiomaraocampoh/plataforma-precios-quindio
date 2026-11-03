from django.contrib import admin

from .models import Denuncia


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ("id", "reporte", "motivo", "estado", "creado_en")
    list_filter = ("estado", "motivo")
    raw_id_fields = ("reporte", "denunciante", "resuelto_por")
