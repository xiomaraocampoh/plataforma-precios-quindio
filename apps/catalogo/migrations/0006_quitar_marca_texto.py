"""Paso 3 de 3: quita el texto Producto.marca y la FK toma su nombre."""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0005_migrar_marca_texto")]

    operations = [
        migrations.RemoveField(model_name="producto", name="marca"),
        migrations.RenameField(model_name="producto", old_name="marca_ref", new_name="marca"),
        migrations.AlterField(
            model_name="producto",
            name="marca",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="productos",
                to="catalogo.marca",
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.UniqueConstraint(
                condition=models.Q(marca__isnull=False),
                fields=("nombre_normalizado", "marca"),
                name="producto_unico_por_marca",
            ),
        ),
        migrations.AddConstraint(
            model_name="producto",
            constraint=models.UniqueConstraint(
                condition=models.Q(marca__isnull=True),
                fields=("nombre_normalizado",),
                name="producto_unico_sin_marca",
            ),
        ),
    ]
