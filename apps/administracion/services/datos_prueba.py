"""Carga de los datos de prueba de data/demo/ (cargar_datos_prueba). Capa de aplicación.

Lee los CSV, valida cada fila con `domain.datos_prueba` y escribe SIEMPRE a través del servicio del
módulo dueño del dato (catálogo, establecimientos, precios, moderación, cuentas). Así los datos de
prueba pasan por las mismas reglas que los reales: normalización y duplicados (D-05), anomalías
(EC-03), una denuncia por persona (RF-20) y «Sigue igual» idempotente (RF-14).

Idempotente: cada fila de precios.csv tiene un id fijo («P0001») que se convierte en un UUID
determinista (`id_cliente`); correr el comando dos veces no duplica nada.
"""

import csv
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalogo import services as catalogo
from apps.catalogo.domain.duplicados import normalizar_nombre
from apps.catalogo.models import Categoria, Marca, Producto, SolicitudCatalogo
from apps.cuentas import services as cuentas
from apps.establecimientos import services as establecimientos
from apps.establecimientos.models import Establecimiento
from apps.moderacion import services as moderacion
from apps.precios import services as precios
from apps.precios.domain.vigencia import Fuente
from apps.precios.models import ConfirmacionPrecio, ReportePrecio
from core.errores import EnUsoError

from ..domain.datos_prueba import (
    FilaInvalidaError,
    fecha_de_observacion,
    leer_cantidad,
    leer_establecimiento,
    leer_fuente,
    leer_precio,
    leer_presentacion,
    leer_si_no,
    leer_unidad,
)

# Espacio de nombres fijo: el UUID de cada fila no cambia entre corridas (idempotencia)
ESPACIO_UUID = uuid.UUID("5b0f5d0e-8e1c-4c47-9a57-6d2f0c0de001")
MARCADOR_SOLICITUD = "[Datos de prueba]"


class DatosDePruebaInvalidosError(ValueError):
    """Una fila de los CSV no se puede cargar; el mensaje dice archivo, línea y motivo."""


@dataclass
class Resumen:
    nuevos: dict[str, int] = field(default_factory=dict)
    totales: dict[str, int] = field(default_factory=dict)
    avisos: list[str] = field(default_factory=list)

    def sumar(self, clave: str, creado: bool) -> None:
        self.totales[clave] = self.totales.get(clave, 0) + 1
        self.nuevos[clave] = self.nuevos.get(clave, 0) + int(creado)


def directorio_por_defecto() -> Path:
    return Path(settings.BASE_DIR) / "data" / "demo"


def _filas(directorio: Path, archivo: str) -> list[tuple[str, dict]]:
    ruta = directorio / archivo
    if not ruta.exists():
        raise DatosDePruebaInvalidosError(f"No existe {ruta}.")
    with ruta.open(encoding="utf-8-sig", newline="") as f:
        # La línea 1 es el encabezado: la primera fila de datos es la línea 2
        return [(f"{archivo} línea {n}", fila) for n, fila in enumerate(csv.DictReader(f), 2)]


def _validar(donde: str, leer: Callable, *args):
    try:
        return leer(*args)
    except (FilaInvalidaError, ValidationError, KeyError) as exc:
        mensaje = " ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
        raise DatosDePruebaInvalidosError(f"{donde}: {mensaje}") from exc


def _clave_presentacion(marca: str, producto: str, cantidad, unidad: str) -> tuple:
    return (normalizar_nombre(marca), normalizar_nombre(producto), cantidad, unidad)


# ---------- catálogo y directorio ----------


def _categorias(directorio: Path, resumen: Resumen) -> dict[str, Categoria]:
    resultado = {}
    for donde, fila in _filas(directorio, "categorias.csv"):
        perecedera = _validar(
            donde, lambda f: leer_si_no(f["perecedera"], campo="perecedera"), fila
        )
        categoria, creada = catalogo.asegurar_categoria(
            nombre=fila["nombre"].strip(), perecedera=perecedera
        )
        resultado[categoria.nombre] = categoria
        resumen.sumar("categorias", creada)
    return resultado


def _marcas(directorio: Path, resumen: Resumen) -> dict[str, Marca]:
    resultado = {}
    for _, fila in _filas(directorio, "marcas.csv"):
        normal = normalizar_nombre(fila["nombre"])
        existia = Marca.objects.filter(nombre_normalizado=normal).exists()
        marca = catalogo.marca_por_nombre(fila["nombre"])  # misma normalización que el registro
        resultado[normal] = marca
        resumen.sumar("marcas", not existia)
    return resultado


def _productos(directorio, categorias, marcas, resumen) -> dict[tuple, Producto]:
    resultado = {}
    for donde, fila in _filas(directorio, "productos.csv"):
        categoria = _validar(donde, lambda f: categorias[f["categoria"].strip()], fila)
        marca = _validar(donde, lambda f: marcas[normalizar_nombre(f["marca"])], fila)
        try:
            producto, creado = catalogo.asegurar_producto(
                nombre=fila["nombre"].strip(), marca=marca, categoria=categoria
            )
        except catalogo.PosibleDuplicadoError as exc:  # D-05: no se crea; se avisa
            resumen.avisos.append(f"{donde}: posible duplicado, no se creó. {exc}")
            continue
        resultado[(normalizar_nombre(marca.nombre), producto.nombre_normalizado)] = producto
        resumen.sumar("productos", creado)
    return resultado


def _presentaciones(directorio, productos, resumen) -> dict[tuple, int]:
    resultado = {}
    for donde, fila in _filas(directorio, "presentaciones.csv"):
        datos = _validar(donde, leer_presentacion, fila)
        producto = productos.get(
            (normalizar_nombre(datos.marca), normalizar_nombre(datos.producto))
        )
        if producto is None:
            resumen.avisos.append(f"{donde}: el producto no se cargó; se omite la presentación.")
            continue
        presentacion, creada = catalogo.asegurar_presentacion(
            producto=producto,
            cantidad=datos.cantidad,
            unidad=datos.unidad,
            codigo_barras=datos.codigo_barras,
        )
        clave = _clave_presentacion(datos.marca, datos.producto, datos.cantidad, datos.unidad)
        resultado[clave] = presentacion.pk
        resumen.sumar("presentaciones", creada)
    return resultado


def _establecimientos(directorio, resumen) -> dict[str, Establecimiento]:
    resultado = {}
    for donde, fila in _filas(directorio, "establecimientos.csv"):
        if fila.get("estado", "aprobado").strip() == "pendiente":
            continue  # las sugerencias se cargan aparte, como las haría un reportante (RF-10)
        datos = _validar(donde, leer_establecimiento, fila)
        local, creado = establecimientos.asegurar_establecimiento(
            nombre=datos.nombre,
            tipo=datos.tipo,
            direccion=datos.direccion,
            barrio=datos.barrio,
            municipio=datos.municipio,
        )
        resultado[local.nombre] = local
        resumen.sumar("establecimientos", creado)
    return resultado


# ---------- precios y escenarios ----------


def _precio(donde, fila, presentaciones, locales, autores, ahora) -> dict:
    clave = _clave_presentacion(
        fila["marca"],
        fila["producto"],
        leer_cantidad(fila["cantidad"]),
        leer_unidad(fila["unidad"]),
    )
    return {
        "autor": autores[fila["autor"].strip()],
        "presentacion_id": presentaciones[clave],
        "establecimiento_id": locales[fila["establecimiento"].strip()].pk,
        "precio": leer_precio(fila["precio"]),
        "fecha_observacion": fecha_de_observacion(
            ahora, dias=fila["dias_atras"], horas=fila["horas_atras"]
        ),
        "fuente": Fuente(leer_fuente(fila["fuente_tipo"])),
        "id_cliente": uuid.uuid5(ESPACIO_UUID, fila["id"].strip()),
    }


def _precios(directorio, presentaciones, locales, autores, ahora, resumen) -> dict[str, int]:
    """Las filas van en orden: las de base de una anomalía antes que el precio anómalo."""
    resultado = {}
    for donde, fila in _filas(directorio, "precios.csv"):
        datos = _validar(donde, _precio, donde, fila, presentaciones, locales, autores, ahora)
        existia = ReportePrecio.objects.filter(id_cliente=datos["id_cliente"]).exists()
        reporte = precios.cargar_reporte_historico(**datos, es_demo=True, revisar_anomalia=True)
        resultado[fila["id"].strip()] = reporte.pk
        resumen.sumar("precios", not existia)
        if reporte.estado == ReportePrecio.Estado.EN_REVISION:
            resumen.sumar("en_revision", not existia)
    return resultado


def _acciones(directorio, reportes, autores, resumen) -> None:
    for donde, fila in _filas(directorio, "acciones.csv"):
        usuario = _validar(donde, lambda f: autores[f["usuario"].strip()], fila)
        reporte_id = _validar(donde, lambda f: reportes[f["precio_id"].strip()], fila)
        accion = fila["accion"].strip()
        if accion == "sigue_igual":
            ya = ConfirmacionPrecio.objects.filter(reporte_id=reporte_id, usuario=usuario).exists()
            if not ya:  # idempotente también entre días distintos
                precios.confirmar_precio(usuario=usuario, reporte_id=reporte_id)
            resumen.sumar("sigue_igual", not ya)
        elif accion == "denuncia":
            try:
                moderacion.denunciar(
                    denunciante=usuario,
                    reporte_id=reporte_id,
                    motivo=fila["motivo"].strip(),
                    detalle=f"{MARCADOR_SOLICITUD} {fila['detalle'].strip()}",
                )
                creada = True
            except moderacion.DenunciaDuplicadaError:
                creada = False
            resumen.sumar("denuncias", creada)
        else:
            raise DatosDePruebaInvalidosError(f"{donde}: acción desconocida «{accion}».")


def _solicitudes(directorio, categorias, autores, resumen) -> None:
    for donde, fila in _filas(directorio, "solicitudes.csv"):
        solicitante = _validar(donde, lambda f: autores[f["solicitante"].strip()], fila)
        categoria = _validar(donde, lambda f: categorias[f["categoria"].strip()], fila)
        nombre, marca = fila["nombre"].strip(), fila["marca"].strip()
        ya = SolicitudCatalogo.objects.filter(
            solicitante=solicitante, nombre=nombre, marca=marca
        ).exists()
        if not ya:
            catalogo.solicitar_producto(
                solicitante=solicitante,
                nombre=nombre,
                marca=marca,
                categoria_id=categoria.pk,
                cantidad=_validar(donde, leer_cantidad, fila["cantidad"]),
                unidad=_validar(donde, leer_unidad, fila["unidad"]),
                codigo_barras=fila.get("codigo_barras", ""),
                detalle=f"{MARCADOR_SOLICITUD} {fila.get('detalle', '').strip()}",
            )
        resumen.sumar("solicitudes", not ya)


def _sugeridos(directorio, autores, resumen) -> None:
    for donde, fila in _filas(directorio, "establecimientos.csv"):
        if fila.get("estado", "").strip() != "pendiente":
            continue
        datos = _validar(donde, leer_establecimiento, fila)
        ya = Establecimiento.objects.filter(nombre=datos.nombre, municipio=datos.municipio).exists()
        if not ya:
            establecimientos.sugerir_establecimiento(
                autor=_validar(donde, lambda f: autores[f["sugerido_por"].strip()], fila),
                nombre=datos.nombre,
                tipo=datos.tipo,
                direccion=datos.direccion,
                barrio=datos.barrio,
                municipio=datos.municipio,
            )
        resumen.sumar("sugeridos", not ya)


# ---------- casos de uso ----------


@transaction.atomic
def cargar(
    *,
    directorio: Path | None = None,
    solo_catalogo: bool = False,
    ahora: datetime | None = None,
) -> Resumen:
    """Carga todo en una transacción: si una fila es inválida no queda nada a medias."""
    directorio = directorio or directorio_por_defecto()
    ahora = ahora or timezone.now()
    resumen = Resumen()
    categorias = _categorias(directorio, resumen)
    productos = _productos(directorio, categorias, _marcas(directorio, resumen), resumen)
    presentaciones = _presentaciones(directorio, productos, resumen)
    locales = _establecimientos(directorio, resumen)
    if solo_catalogo:
        return resumen
    cuentas.cuentas_prueba.asegurar_cuentas_prueba(contrasena=None)  # autores (sin contraseña)
    autores = cuentas.cuentas_prueba.usuarios_de_prueba()
    reportes = _precios(directorio, presentaciones, locales, autores, ahora, resumen)
    _acciones(directorio, reportes, autores, resumen)
    _solicitudes(directorio, categorias, autores, resumen)
    _sugeridos(directorio, autores, resumen)
    return resumen


def _borrar_si_libre(objetos, eliminar: Callable) -> int:
    borrados = 0
    for objeto in objetos:
        try:
            eliminar(objeto)
        except EnUsoError:  # lo usa un dato real: se conserva
            continue
        borrados += 1
    return borrados


def _nombres(directorio: Path, archivo: str, campo: str) -> set[str]:
    return {fila[campo].strip() for _, fila in _filas(directorio, archivo)}


def _productos_del_csv(directorio: Path) -> list[Producto]:
    claves = {
        (normalizar_nombre(f["marca"]), normalizar_nombre(f["nombre"]))
        for _, f in _filas(directorio, "productos.csv")
    }
    candidatos = Producto.objects.select_related("marca").filter(
        nombre_normalizado__in={nombre for _, nombre in claves}
    )
    return [
        p
        for p in candidatos
        if (p.marca.nombre_normalizado if p.marca else "", p.nombre_normalizado) in claves
    ]


@transaction.atomic
def limpiar(*, directorio: Path | None = None) -> dict[str, int]:
    """Borra los datos de prueba. Lo que también usan datos reales se conserva."""
    directorio = directorio or directorio_por_defecto()
    borrados = {
        "precios": precios.borrar_reportes_demo(),
        "solicitudes": catalogo.borrar_solicitudes_pendientes(marcador=MARCADOR_SOLICITUD),
    }
    locales = Establecimiento.objects.filter(
        nombre__in=_nombres(directorio, "establecimientos.csv", "nombre")
    )
    borrados["establecimientos"] = _borrar_si_libre(locales, establecimientos.eliminar)
    borrados["productos"] = _borrar_si_libre(_productos_del_csv(directorio), catalogo.eliminar)
    normales = {normalizar_nombre(n) for n in _nombres(directorio, "marcas.csv", "nombre")}
    marcas = Marca.objects.filter(nombre_normalizado__in=normales)
    borrados["marcas"] = _borrar_si_libre(marcas, catalogo.eliminar)
    categorias = Categoria.objects.filter(
        nombre__in=_nombres(directorio, "categorias.csv", "nombre")
    )
    borrados["categorias"] = _borrar_si_libre(categorias, catalogo.eliminar)
    return borrados
