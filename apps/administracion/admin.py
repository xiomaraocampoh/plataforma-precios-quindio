from django.contrib import admin

from .models import RegistroAuditoria


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    """Solo lectura: la bitácora del panel no se edita ni se borra (M-14)."""

    list_display = ("creado_en", "actor", "accion", "entidad", "objeto")
    list_filter = ("accion", "entidad")
    search_fields = ("objeto", "actor__username")
    list_select_related = ("actor",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
