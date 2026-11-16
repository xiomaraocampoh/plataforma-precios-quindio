"""Carga datos de demostración (catálogo, establecimientos, usuarios y precios).

Uso: python manage.py cargar_demo [--con-vencidos]

- Los precios se cargan con `services.cargar_reporte_historico`: son datos históricos, fechados
  cuando se «observaron», así que no consumen el cupo de registros por hora (RN-10) y se puede
  probar el registro con `demo` justo después de cargar. Cada parte es idempotente.
- Accesos: superusuario «admin» y moderador «moderador_demo» (rol moderador, is_staff). Su
  contraseña sale de DEMO_ADMIN_PASSWORD; la de los usuarios demo, de DEMO_PASSWORD. Si la variable
  no existe se genera una aleatoria y se muestra UNA vez en consola. Nunca hay contraseñas en el
  código ni en el README.
- --con-vencidos: precios justo fuera de la ventana de vigencia (8 días reportado, 4 días
  perecedero, 31 días oficial) y justo dentro (6, 2 y 29 días), para comprobar EC-02.
"""

import os
import secrets
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.cuentas import services as cuentas
from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento
from apps.precios import services
from apps.precios.domain.vigencia import Fuente
from apps.precios.models import ReportePrecio

USUARIOS_DEMO = ["demo", "demo_ana", "demo_luis", "demo_sofia"]
ADMIN = "admin"
MODERADOR = "moderador_demo"

CATEGORIAS = {"Granos": False, "Abarrotes": False, "Lácteos y huevos": True, "Frescos": True}

# (producto, categoría, [(cantidad, unidad, precio base COP)])
PRODUCTOS = [
    ("Arroz blanco", "Granos", [("500", "g", 2600), ("1", "kg", 4900)]),
    ("Lentejas", "Granos", [("500", "g", 4200)]),
    ("Leche entera", "Lácteos y huevos", [("1", "L", 4600), ("900", "ml", 4300)]),
    ("Huevos AA", "Lácteos y huevos", [("12", "und", 9800), ("30", "und", 23500)]),
    ("Panela", "Abarrotes", [("500", "g", 3200)]),
    ("Aceite vegetal", "Abarrotes", [("1", "L", 11800), ("3", "L", 33500)]),
    ("Café molido", "Abarrotes", [("250", "g", 8900)]),
    ("Papa pastusa", "Frescos", [("1", "kg", 3100)]),
    ("Tomate chonto", "Frescos", [("1", "kg", 4800)]),
]

# (nombre, tipo, dirección, barrio, latitud, longitud, factor de precio)
ESTABLECIMIENTOS = [
    ("Tienda Doña Rosa", "tienda", "Cra 14 # 10-20", "Centro", "4.533889", "-75.681111", 1.03),
    (
        "Tienda El Vecino",
        "tienda",
        "Cl 5N # 16-30",
        "Los Fundadores",
        "4.548100",
        "-75.668900",
        1.06,
    ),
    (
        "Minimercado La Esquina",
        "minimercado",
        "Cra 19 # 14-55",
        "Granada",
        "4.535200",
        "-75.673400",
        1.01,
    ),
    (
        "Minimercado Nuevo Centro",
        "minimercado",
        "Cl 21 # 15-12",
        "Centro",
        "4.538700",
        "-75.676200",
        0.99,
    ),
    (
        "Supermercado Central",
        "supermercado",
        "Av. Bolívar # 12-40",
        "Centro",
        "4.536500",
        "-75.678800",
        0.95,
    ),
    (
        "Supermercado del Parque",
        "supermercado",
        "Cl 19 # 15-10",
        "Centro",
        "4.537900",
        "-75.675100",
        0.97,
    ),
]


# --con-vencidos: (producto, categoría, cantidad, unidad, [(establecimiento, días, fuente, precio)])
VENCIDOS = [
    (
        "Frijol cargamanto",
        "Granos",
        "500",
        "g",
        [
            ("Tienda Doña Rosa", 8, Fuente.REPORTANTE, 5200),  # vencido: ventana de 7 días
            ("Tienda El Vecino", 6, Fuente.REPORTANTE, 5300),  # vigente
            ("Supermercado Central", 31, Fuente.COMERCIO, 4900),  # vencido: oficial, 30 días
            ("Supermercado del Parque", 29, Fuente.COMERCIO, 5000),  # vigente
        ],
    ),
    (
        "Queso campesino",
        "Lácteos y huevos",
        "500",
        "g",
        [
            ("Minimercado La Esquina", 4, Fuente.REPORTANTE, 9800),  # vencido: perecedero, 3 días
            ("Minimercado Nuevo Centro", 2, Fuente.REPORTANTE, 9600),  # vigente
        ],
    ),
]


def _clave(variable: str) -> tuple[str, bool]:
    """(contraseña, generada): de la variable de entorno o aleatoria si no existe."""
    valor = os.environ.get(variable, "")
    return (valor, False) if valor else (secrets.token_urlsafe(12), True)


def _redondear(valor: float) -> Decimal:
    return Decimal(round(valor / 50) * 50)


class Command(BaseCommand):
    help = "Carga datos de demostración con precios de ejemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--con-vencidos",
            action="store_true",
            help="Agrega precios justo fuera y justo dentro de la ventana de vigencia (EC-02).",
        )

    @transaction.atomic
    def handle(self, *args, **opciones):
        if ReportePrecio.objects.filter(autor__username__in=USUARIOS_DEMO).exists():
            self.stdout.write("Ya hay datos de demostración; no se cargaron precios base.")
        else:
            usuarios = self._usuarios()
            n = self._precios(usuarios, self._establecimientos(), self._catalogo())
            self.stdout.write(self.style.SUCCESS(f"Listo: {n} precios de ejemplo cargados."))
        self._accesos()
        if opciones["con_vencidos"]:
            self._vencidos()

    def _avisar_clave(self, usuarios: str, variable: str, clave: str, generada: bool) -> None:
        if generada:
            self.stdout.write(
                self.style.WARNING(
                    f"Contraseña generada para {usuarios} (defina {variable} para fijarla; "
                    f"no se volverá a mostrar): {clave}"
                )
            )
        else:
            self.stdout.write(f"{usuarios}: contraseña tomada de {variable}.")

    def _usuarios(self) -> list[Usuario]:
        clave, generada = _clave("DEMO_PASSWORD")
        usuarios = [
            cuentas.registrar_usuario(username=u, email="", password=clave) for u in USUARIOS_DEMO
        ]
        self._avisar_clave(", ".join(USUARIOS_DEMO), "DEMO_PASSWORD", clave, generada)
        return usuarios

    def _accesos(self) -> None:
        clave, generada = _clave("DEMO_ADMIN_PASSWORD")
        _, admin_nuevo = cuentas.asegurar_administrador(username=ADMIN, password=clave)
        _, mod_nuevo = cuentas.asegurar_moderador(username=MODERADOR, password=clave)
        nuevos = [u for u, nuevo in ((ADMIN, admin_nuevo), (MODERADOR, mod_nuevo)) if nuevo]
        if nuevos:
            self._avisar_clave(" y ".join(nuevos), "DEMO_ADMIN_PASSWORD", clave, generada)
        else:
            self.stdout.write(f"{ADMIN} y {MODERADOR} ya existen; no se cambió su contraseña.")

    def _vencidos(self) -> None:
        autor = Usuario.objects.get(username=USUARIOS_DEMO[0])
        cats = {c.nombre: c for c in Categoria.objects.all()}
        locales = {e.nombre: e for e in Establecimiento.objects.all()}
        ahora = timezone.now()
        creados = 0
        for nombre, cat, cantidad, unidad, filas in VENCIDOS:
            producto, _ = Producto.objects.get_or_create(
                nombre_normalizado=normalizar_nombre(nombre),
                marca="",
                defaults={"nombre": nombre, "categoria": cats[cat]},
            )
            pres, _ = Presentacion.objects.get_or_create(
                producto=producto, cantidad=Decimal(cantidad), unidad=unidad
            )
            if ReportePrecio.objects.filter(presentacion=pres).exists():
                continue
            for local, dias, fuente, precio in filas:
                services.cargar_reporte_historico(
                    autor=autor,
                    presentacion_id=pres.pk,
                    establecimiento_id=locales[local].pk,
                    precio=Decimal(precio),
                    fecha_observacion=ahora - timedelta(days=dias),
                    fuente=fuente,
                )
                creados += 1
        self.stdout.write(f"Precios vencidos y en el límite de vigencia: {creados} nuevos.")

    def _establecimientos(self) -> list[tuple[Establecimiento, float]]:
        return [
            (
                Establecimiento.objects.get_or_create(
                    nombre=nombre,
                    defaults={
                        "tipo": tipo,
                        "direccion": direccion,
                        "barrio": barrio,
                        "latitud": Decimal(lat),
                        "longitud": Decimal(lon),
                    },
                )[0],
                factor,
            )
            for nombre, tipo, direccion, barrio, lat, lon, factor in ESTABLECIMIENTOS
        ]

    def _catalogo(self) -> list[tuple[Presentacion, int]]:
        cats = {
            n: Categoria.objects.get_or_create(nombre=n, defaults={"perecedera": p})[0]
            for n, p in CATEGORIAS.items()
        }
        resultado = []
        for nombre, cat, presentaciones in PRODUCTOS:
            producto, _ = Producto.objects.get_or_create(
                nombre_normalizado=normalizar_nombre(nombre),
                marca="",
                defaults={"nombre": nombre, "categoria": cats[cat]},
            )
            for cantidad, unidad, base in presentaciones:
                pres, _ = Presentacion.objects.get_or_create(
                    producto=producto, cantidad=Decimal(cantidad), unidad=unidad
                )
                resultado.append((pres, base))
        return resultado

    def _precios(self, usuarios, locales, presentaciones) -> int:
        ahora = timezone.now()
        total = 0
        for i, (pres, base) in enumerate(presentaciones):
            for j, (local, factor) in enumerate(locales):
                variacion = ((i * 7 + j * 13) % 5 - 2) / 100  # determinista: ±2 %
                precio = _redondear(base * (factor + variacion))
                horas = 2 + (i * 5 + j * 3) % 40
                autor = usuarios[(i + j) % len(usuarios)]
                self._registrar(autor, pres, local, precio, ahora - timedelta(hours=horas))
                total += 1
                if (i + j) % 3 == 0:  # confirmación independiente: sube la confiabilidad
                    otro = usuarios[(i + j + 1) % len(usuarios)]
                    self._registrar(otro, pres, local, precio, ahora - timedelta(hours=horas + 20))
                    total += 1
        return total

    @staticmethod
    def _registrar(autor, pres, local, precio, fecha) -> None:
        services.cargar_reporte_historico(
            autor=autor,
            presentacion_id=pres.pk,
            establecimiento_id=local.pk,
            precio=precio,
            fecha_observacion=fecha,
        )
