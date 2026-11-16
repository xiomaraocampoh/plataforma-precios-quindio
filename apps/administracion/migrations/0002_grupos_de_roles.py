"""Crea los grupos Administrador, Moderador, Editor de catálogo y Reportante con sus permisos.

- Los permisos salen de apps.cuentas.domain.roles (la misma fuente que usa el servicio).
- El grupo anterior «Moderadores» se convierte en «Moderador» y conserva a sus integrantes.
- Cada usuario existente queda en el grupo de su `rol`.
- En una base nueva los permisos aún no existen (se crean después de migrar): se crean aquí.
La reversa no borra grupos: quitarlos dejaría a usuarios sin permisos.
"""

from django.contrib.auth.management import create_permissions
from django.db import migrations
from django.db.models import Q

from apps.cuentas.domain.roles import GRUPOS, PERMISOS, grupo_de

GRUPO_ANTERIOR = "Moderadores"


def _crear_permisos(apps):
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None


def _permisos(Permission, nombres):
    filtro = Q(pk__in=[])
    for nombre in nombres:
        app, codigo = nombre.split(".", 1)
        filtro |= Q(content_type__app_label=app, codename=codigo)
    return Permission.objects.filter(filtro)


def _renombrar_grupo_anterior(Group):
    anterior = Group.objects.filter(name=GRUPO_ANTERIOR).first()
    if anterior is None:
        return
    nuevo = Group.objects.filter(name=GRUPOS["moderador"]).first()
    if nuevo is None:
        anterior.name = GRUPOS["moderador"]
        anterior.save(update_fields=["name"])
        return
    nuevo.user_set.add(*anterior.user_set.all())
    anterior.delete()


def crear_grupos(apps, schema_editor):
    _crear_permisos(apps)
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    Usuario = apps.get_model("cuentas", "Usuario")

    _renombrar_grupo_anterior(Group)
    grupos = {}
    for rol, nombre in GRUPOS.items():
        grupo, _ = Group.objects.get_or_create(name=nombre)
        grupo.permissions.set(_permisos(Permission, PERMISOS[rol]))
        grupos[nombre] = grupo

    de_rol = list(grupos.values())
    for usuario in Usuario.objects.all():
        usuario.groups.remove(*de_rol)
        nombre = grupo_de(usuario.rol)
        if nombre:
            usuario.groups.add(grupos[nombre])


class Migration(migrations.Migration):
    dependencies = [
        ("administracion", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("cuentas", "0003_roles_y_permiso_gestionar_cuentas"),
        ("catalogo", "0007_activos"),
        ("establecimientos", "0002_sugerencias_y_moderacion"),
        ("precios", "0002_confirmacion_precio"),
        ("moderacion", "0002_decision_moderacion"),
    ]

    operations = [migrations.RunPython(crear_grupos, migrations.RunPython.noop)]
