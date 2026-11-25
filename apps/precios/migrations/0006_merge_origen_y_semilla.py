# Une la rama de esquema (0005, origen del reporte) con la de la siembra (0004). Sin operaciones.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('precios', '0004_semilla_precios_prueba'),
        ('precios', '0005_reporte_origen'),
    ]

    operations = []
