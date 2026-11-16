from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.moderacion import services as moderacion
from core.admin_acciones import accion_de_moderacion

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Plataforma",
            {
                "fields": (
                    "rol",
                    "acepto_tratamiento_datos",
                    "fecha_aceptacion_datos",
                    "suprimido_en",
                )
            },
        ),
    )
    readonly_fields = ("suprimido_en",)
    list_display = ("username", "email", "rol", "is_active")
    list_filter = ("rol", "is_active")
    actions = [
        accion_de_moderacion(
            "Suspender cuentas",
            lambda m, u: moderacion.suspender_cuenta(moderador=m, usuario_id=u.pk),
        )
    ]
