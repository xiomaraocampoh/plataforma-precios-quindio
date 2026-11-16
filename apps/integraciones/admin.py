from django.contrib import admin

from .models import PrecioReferencia


@admin.register(PrecioReferencia)
class PrecioReferenciaAdmin(admin.ModelAdmin):
    list_display = ("producto", "mercado", "precio_por_kg", "fecha", "fuente")
    list_filter = ("fuente", "mercado")
    search_fields = ("producto__nombre", "mercado")
    date_hierarchy = "fecha"
    list_select_related = ("producto",)
