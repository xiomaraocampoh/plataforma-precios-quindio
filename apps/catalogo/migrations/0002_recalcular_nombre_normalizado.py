"""Recalcula Producto.nombre_normalizado con la regla D-05 (conserva la ñ; RF-04, RF-06)."""

from django.db import migrations

from apps.catalogo.domain.duplicados import normalizar_nombre


def recalcular(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.only("id", "nombre", "nombre_normalizado"):
        nuevo = normalizar_nombre(producto.nombre)
        if producto.nombre_normalizado != nuevo:
            producto.nombre_normalizado = nuevo
            producto.save(update_fields=["nombre_normalizado"])


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0001_initial")]

    operations = [migrations.RunPython(recalcular, migrations.RunPython.noop)]
