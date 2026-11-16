from django.contrib import admin

from apps.moderacion import services as moderacion
from core.admin_acciones import accion_de_moderacion

from .models import Categoria, Marca, Presentacion, Producto, SolicitudCatalogo


class PresentacionInline(admin.TabularInline):
    model = Presentacion
    extra = 1


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "marca", "categoria", "activo")
    search_fields = (
        "nombre",
        "marca__nombre",
        "nombre_normalizado",
        "presentaciones__codigo_barras",
    )
    list_filter = ("categoria", "marca", "activo")
    list_select_related = ("categoria", "marca")
    autocomplete_fields = ("marca",)
    inlines = [PresentacionInline]


@admin.register(Presentacion)
class PresentacionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "unidad", "codigo_barras")
    list_filter = ("unidad", "producto__categoria", "producto__marca")
    search_fields = ("codigo_barras", "producto__nombre", "producto__marca__nombre")
    list_select_related = ("producto__marca",)
    autocomplete_fields = ("producto",)


@admin.register(SolicitudCatalogo)
class SolicitudCatalogoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "categoria", "estado", "creado_en", "resuelto_por")
    list_filter = ("estado", "categoria")
    search_fields = ("nombre", "marca", "codigo_barras")
    readonly_fields = ("solicitante", "resuelto_por", "resuelto_en", "presentacion_creada")
    actions = [
        accion_de_moderacion(
            "Aprobar y agregar al catálogo",
            lambda m, s: moderacion.decidir_solicitud(moderador=m, solicitud_id=s.pk, aprobar=True),
        ),
        accion_de_moderacion(
            "Rechazar solicitudes",
            lambda m, s: moderacion.decidir_solicitud(
                moderador=m, solicitud_id=s.pk, aprobar=False
            ),
        ),
    ]


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre", "nombre_normalizado")
    readonly_fields = ("nombre_normalizado",)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "perecedera", "activa")
    list_filter = ("perecedera", "activa")
    search_fields = ("nombre",)
