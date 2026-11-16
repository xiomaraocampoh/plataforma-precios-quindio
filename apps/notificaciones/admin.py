from django.contrib import admin

from .models import CorreoPendiente


@admin.register(CorreoPendiente)
class CorreoPendienteAdmin(admin.ModelAdmin):
    """Solo lectura: el estado de la cola se cambia con `manage.py enviar_correos`."""

    list_display = ("creado_en", "tipo", "estado", "intentos", "enviado_en")
    list_filter = ("estado", "tipo")
    readonly_fields = [f.name for f in CorreoPendiente._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
