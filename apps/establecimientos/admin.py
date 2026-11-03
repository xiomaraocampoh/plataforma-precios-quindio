from django.contrib import admin

from .models import Establecimiento


@admin.register(Establecimiento)
class EstablecimientoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "tipo", "barrio", "municipio", "activo")
    list_filter = ("tipo", "municipio", "activo")
    search_fields = ("nombre", "barrio", "direccion")
