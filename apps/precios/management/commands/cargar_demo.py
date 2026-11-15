"""Carga datos de demostración (catálogo, establecimientos, usuarios y precios).

Uso: python manage.py cargar_demo
Los precios se registran mediante `services.registrar_reporte` para respetar las reglas de negocio
(vigencia, anomalías, caché). Es idempotente: si ya hay datos demo, no hace nada.
"""

import unicodedata
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalogo.models import Categoria, Presentacion, Producto
from apps.cuentas import services as cuentas
from apps.cuentas.models import Usuario
from apps.establecimientos.models import Establecimiento
from apps.precios import services
from apps.precios.models import ReportePrecio

CLAVE_DEMO = "Demo-2026-precios"  # solo desarrollo

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


def _normalizar(texto: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower().strip()


def _redondear(valor: float) -> Decimal:
    return Decimal(round(valor / 50) * 50)


class Command(BaseCommand):
    help = "Carga datos de demostración con precios de ejemplo."

    @transaction.atomic
    def handle(self, *args, **opciones):
        if ReportePrecio.objects.filter(autor__username__startswith="demo").exists():
            self.stdout.write("Ya hay datos de demostración; no se cargó nada.")
            return

        usuarios = self._usuarios()
        locales = self._establecimientos()
        presentaciones = self._catalogo()
        n = self._precios(usuarios, locales, presentaciones)

        self.stdout.write(self.style.SUCCESS(f"Listo: {n} precios de ejemplo cargados."))
        self.stdout.write(f"Usuario de prueba: demo  ·  contraseña: {CLAVE_DEMO}")

    def _usuarios(self) -> list[Usuario]:
        nombres = ["demo", "demo_ana", "demo_luis", "demo_sofia"]
        return [
            cuentas.registrar_usuario(username=u, email="", password=CLAVE_DEMO) for u in nombres
        ]

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
                nombre_normalizado=_normalizar(nombre),
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
        services.registrar_reporte(
            autor=autor,
            presentacion_id=pres.pk,
            establecimiento_id=local.pk,
            precio=precio,
            fecha_observacion=fecha,
        )
