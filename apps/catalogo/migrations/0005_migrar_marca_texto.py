"""Paso 2 de 3: el texto de Producto.marca pasa a Marca (y vuelve en la reversa).

- Las variantes de una misma marca («Águila Roja», «aguila  roja») se unen en una sola, con la
  primera grafía registrada. Una marca vacía o solo con espacios queda en NULL (sin marca).
- Si al unir variantes dos productos quedarían repetidos (mismo nombre y marca), la migración se
  detiene y los lista: fusionarlos es una decisión de moderación (D-05), no de una migración.
"""

from django.db import migrations
from django.db.models import Count

from apps.catalogo.domain.duplicados import normalizar_nombre


def texto_a_marca(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    Marca = apps.get_model("catalogo", "Marca")
    marcas: dict[str, object] = {}
    for producto in Producto.objects.exclude(marca="").order_by("pk"):
        nombre = " ".join(producto.marca.split())
        normal = normalizar_nombre(nombre)
        if not normal:
            continue
        if normal not in marcas:
            marcas[normal] = Marca.objects.create(nombre=nombre, nombre_normalizado=normal)
        producto.marca_ref = marcas[normal]
        producto.save(update_fields=["marca_ref"])

    repetidos = (
        Producto.objects.values("nombre_normalizado", "marca_ref")
        .annotate(n=Count("id"))
        .filter(n__gt=1)
    )
    if repetidos:
        lista = ", ".join(
            f"«{r['nombre_normalizado']}» (marca {r['marca_ref'] or 'ninguna'}: {r['n']} productos)"
            for r in repetidos
        )
        raise RuntimeError(
            f"Productos que quedarían duplicados al unificar marcas: {lista}. "
            "Fusiónelos o renómbrelos antes de migrar."
        )


def marca_a_texto(apps, schema_editor):
    Producto = apps.get_model("catalogo", "Producto")
    for producto in Producto.objects.filter(marca_ref__isnull=False).select_related("marca_ref"):
        producto.marca = producto.marca_ref.nombre
        producto.save(update_fields=["marca"])


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0004_marca")]

    operations = [migrations.RunPython(texto_a_marca, marca_a_texto)]
