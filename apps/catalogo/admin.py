from django.contrib import admin

from .models import Categoria, Presentacion, Producto


class PresentacionInline(admin.TabularInline):
    model = Presentacion
    extra = 1


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "marca", "categoria")
    search_fields = ("nombre", "marca", "nombre_normalizado")
    list_filter = ("categoria",)
    inlines = [PresentacionInline]


admin.site.register(Categoria)
