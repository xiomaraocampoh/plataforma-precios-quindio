from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Plataforma", {"fields": ("rol", "acepto_tratamiento_datos", "fecha_aceptacion_datos")}),
    )
    list_display = ("username", "email", "rol", "is_active")
    list_filter = ("rol", "is_active")
