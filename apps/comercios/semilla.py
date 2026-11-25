"""Siembra de comercios de prueba (ADR-0023). La usa la migración `0002_semilla_comercios_prueba`.

`cargar_datos_prueba` (administracion) no la llama: eso haría que el núcleo importe el módulo
comercial (contrato `comercios-no-adelantado`). Con `--limpiar`, las dos tiendas y los productos con
precio oficial se conservan, como todo lo que tiene datos que dependen de ello.

Recibe el registro de modelos (`apps`): no importa modelos ni servicios. Siembra dos comercios
VERIFICADOS por `moderador_prueba`, con precios oficiales y una promoción de cada tipo:

- «Tienda Doña Gloria», de la cuenta de prueba `comercio_prueba` (ya existe, rol comercio).
- «Tienda El Paisa», de la cuenta `comercio_paisa_prueba`, que se crea aquí sin contraseña
  utilizable: solo es la dueña del perfil.

No cambia datos existentes: si el establecimiento ya tiene un perfil, no lo toca. Las fechas son
relativas a `ahora` (vigencia de 30 días y promociones que empezaron ayer).
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password

from apps.catalogo.domain.duplicados import normalizar_nombre
from core.semilla import MARCADOR_PRUEBA

from .domain.promociones import (
    DescuentoPorcentual,
    PagueXLleveY,
    PrecioEspecial,
    Vigencia,
)
from .domain.promociones import Promocion as PromocionDominio

MODERADOR = "moderador_prueba"
DUENA_NUEVA = "comercio_paisa_prueba"


@dataclass(frozen=True)
class Oficial:
    producto: str
    marca: str
    cantidad: Decimal
    unidad: str
    precio: Decimal


@dataclass(frozen=True)
class PromocionPrueba:
    oficial: int  # índice en `oficiales`
    tipo: str
    datos: dict
    motivo: str
    condiciones: str


@dataclass(frozen=True)
class ComercioPrueba:
    establecimiento: str
    usuario: str
    contacto: str
    oficiales: tuple[Oficial, ...]
    promociones: tuple[PromocionPrueba, ...]


COMERCIOS: tuple[ComercioPrueba, ...] = (
    ComercioPrueba(
        "Tienda Doña Gloria",
        "comercio_prueba",
        "Gloria (prueba)",
        (
            Oficial("Arroz blanco", "Supremo", Decimal("1"), "kg", Decimal("5900")),
            Oficial("Azúcar blanca", "Riopaila", Decimal("500"), "g", Decimal("2600")),
            Oficial("Huevos AA rojos", "Kikes", Decimal("30"), "und", Decimal("23500")),
        ),
        (
            PromocionPrueba(
                0,
                "descuento_porcentual",
                {"porcentaje": Decimal("10")},
                "temporada",
                "Hasta agotar existencias.",
            ),
            PromocionPrueba(
                1,
                "pague_x_lleve_y",
                {"pague": 2, "lleve": 3},
                "liquidacion",
                "Máximo 6 unidades por compra.",
            ),
        ),
    ),
    ComercioPrueba(
        "Tienda El Paisa",
        DUENA_NUEVA,
        "Don Paisa (prueba)",
        (
            Oficial("Arroz blanco", "Supremo", Decimal("1"), "kg", Decimal("6000")),
            Oficial("Café molido", "Águila Roja", Decimal("500"), "g", Decimal("28500")),
        ),
        (
            PromocionPrueba(
                1,
                "precio_especial",
                {"precio_especial": Decimal("26900")},
                "lanzamiento",
                "Solo en el local; no aplica con otras promociones.",
            ),
        ),
    ),
)


def _presentacion(apps, o: Oficial):
    Presentacion = apps.get_model("catalogo", "Presentacion")
    candidatas = Presentacion.objects.filter(
        producto__nombre_normalizado=normalizar_nombre(o.producto),
        cantidad=o.cantidad,
        unidad=o.unidad,
        activa=True,
    ).select_related("producto__marca")
    marca = normalizar_nombre(o.marca)
    con_marca = (p for p in candidatas if p.producto.marca)
    return next((p for p in con_marca if p.producto.marca.nombre_normalizado == marca), None)


def _duena(apps, comercio: ComercioPrueba, ahora):
    Usuario = apps.get_model("cuentas", "Usuario")
    usuario = Usuario.objects.filter(username=comercio.usuario).first()
    if usuario is not None or comercio.usuario != DUENA_NUEVA:
        return usuario
    return Usuario.objects.create(
        username=DUENA_NUEVA,
        email="paisa+comercio@example.com",
        password=make_password(None),  # inutilizable: nadie ingresa con esta cuenta
        rol="comercio",
        acepto_tratamiento_datos=True,
        fecha_aceptacion_datos=ahora,
        email_verificado_en=ahora,
        es_cuenta_prueba=True,
    )


def _validar_promocion(p: PromocionPrueba, regular: Decimal, ahora) -> None:
    """La misma regla del dominio que aplica el servicio: si no es válida, falla la siembra."""
    estrategias = {
        "descuento_porcentual": lambda d: DescuentoPorcentual(d["porcentaje"]),
        "precio_especial": lambda d: PrecioEspecial(d["precio_especial"]),
        "pague_x_lleve_y": lambda d: PagueXLleveY(pague=d["pague"], lleve=d["lleve"]),
    }
    PromocionDominio(
        estrategia=estrategias[p.tipo](p.datos),
        precio_regular=regular,
        vigencia=Vigencia(ahora - timedelta(days=1), ahora + timedelta(days=14)),
    )


def _sembrar_comercio(apps, comercio: ComercioPrueba, moderador, ahora, avisos) -> bool:
    Establecimiento = apps.get_model("establecimientos", "Establecimiento")
    PerfilComercio = apps.get_model("comercios", "PerfilComercio")
    PrecioOficial = apps.get_model("comercios", "PrecioOficial")
    Promocion = apps.get_model("comercios", "Promocion")
    local = Establecimiento.objects.filter(nombre=comercio.establecimiento, activo=True).first()
    duena = _duena(apps, comercio, ahora)
    if local is None or duena is None:
        avisos.append(f"{comercio.establecimiento}: falta el local o la cuenta; no se siembra.")
        return False
    if PerfilComercio.objects.filter(establecimiento=local).exclude(estado="rechazado").exists():
        return False  # no se cambian datos existentes
    perfil = PerfilComercio.objects.create(
        usuario=duena,
        establecimiento=local,
        nombre_contacto=comercio.contacto,
        evidencia=f"{MARCADOR_PRUEBA} NIT de prueba",
        codigo_verificacion="PRUEBA",
        estado="verificado",
        verificado_por=moderador,
        verificado_en=ahora,
    )
    oficiales = []
    for o in comercio.oficiales:
        presentacion = _presentacion(apps, o)
        if presentacion is None:
            avisos.append(f"{comercio.establecimiento}: no existe {o.producto} {o.marca}.")
            oficiales.append(None)
            continue
        oficiales.append(
            PrecioOficial.objects.create(
                perfil=perfil, presentacion=presentacion, precio=o.precio, confirmado_en=ahora
            )
        )
    for p in comercio.promociones:
        oficial = oficiales[p.oficial]
        if oficial is None:
            continue
        _validar_promocion(p, oficial.precio, ahora)
        Promocion.objects.create(
            perfil=perfil,
            presentacion=oficial.presentacion,
            tipo=p.tipo,
            inicio=ahora - timedelta(days=1),
            fin=ahora + timedelta(days=14),
            motivo=p.motivo,
            condiciones=f"{p.condiciones} {MARCADOR_PRUEBA}",
            **p.datos,
        )
    return True


def sembrar(apps, *, ahora) -> tuple[int, list[str]]:
    """Devuelve (comercios nuevos, avisos). Necesita la cuenta `moderador_prueba`."""
    Usuario = apps.get_model("cuentas", "Usuario")
    moderador = Usuario.objects.filter(username=MODERADOR).first()
    if moderador is None:
        return 0, ["Comercios de prueba: falta la cuenta moderador_prueba; no se siembran."]
    avisos: list[str] = []
    nuevos = sum(_sembrar_comercio(apps, c, moderador, ahora, avisos) for c in COMERCIOS)
    return nuevos, avisos


def revertir(apps) -> None:
    """Borra solo lo sembrado: perfiles con la evidencia marcada y la cuenta creada aquí."""
    PerfilComercio = apps.get_model("comercios", "PerfilComercio")
    Usuario = apps.get_model("cuentas", "Usuario")
    perfiles = PerfilComercio.objects.filter(evidencia__startswith=MARCADOR_PRUEBA)
    for perfil in perfiles:
        perfil.promociones.all().delete()
        perfil.precios.all().delete()
        perfil.correcciones.all().delete()
    perfiles.delete()
    Usuario.objects.filter(username=DUENA_NUEVA, es_cuenta_prueba=True).delete()
