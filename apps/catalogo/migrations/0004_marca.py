"""Paso 1 de 3: crea Marca y una FK temporal (marca_ref) junto al texto Producto.marca.

La restricción única sobre el texto se quita aquí y se repone en la reversa de este paso, cuando
0005 ya devolvió el texto: así la reversa nunca choca con valores vacíos.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("catalogo", "0003_solicitud_catalogo")]

    operations = [
        migrations.CreateModel(
            name="Marca",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("nombre", models.CharField(max_length=80)),
                ("nombre_normalizado", models.CharField(max_length=80, unique=True)),
                ("activa", models.BooleanField(default=True)),
            ],
            options={"ordering": ["nombre"]},
        ),
        migrations.RemoveConstraint(model_name="producto", name="producto_unico_por_marca"),
        migrations.AddField(
            model_name="producto",
            name="marca_ref",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="+",
                to="catalogo.marca",
            ),
        ),
    ]
