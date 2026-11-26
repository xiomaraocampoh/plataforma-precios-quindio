from django.db import migrations, models


def asignar_departamento(apps, schema_editor):
    """Cada categoría existente queda en el departamento que le corresponde por su nombre."""
    from apps.catalogo.domain.grupos import grupo_sugerido

    Categoria = apps.get_model("catalogo", "Categoria")
    for categoria in Categoria.objects.all():
        categoria.grupo = grupo_sugerido(categoria.nombre)
        categoria.save(update_fields=["grupo"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0010_descripcion_producto"),
    ]

    operations = [
        migrations.AddField(
            model_name="categoria",
            name="grupo",
            field=models.CharField(
                choices=[
                    ("mercado", "Mercado"),
                    ("frutas_verduras", "Frutas y verduras"),
                    ("carnes_pescado", "Carnes y pescado"),
                    ("lacteos_huevos", "Lácteos y huevos"),
                    ("bebidas", "Bebidas"),
                    ("aseo_hogar", "Aseo del hogar"),
                    ("salud_belleza", "Salud y belleza"),
                    ("otros", "Otros"),
                ],
                default="otros",
                max_length=20,
            ),
        ),
        # Primero se asignan los departamentos y después se exige que sean válidos
        migrations.RunPython(asignar_departamento, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="categoria",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "grupo__in",
                        [
                            "mercado",
                            "frutas_verduras",
                            "carnes_pescado",
                            "lacteos_huevos",
                            "bebidas",
                            "aseo_hogar",
                            "salud_belleza",
                            "otros",
                        ],
                    )
                ),
                name="categoria_grupo_valido",
            ),
        ),
    ]
