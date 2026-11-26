"""Lecturas del módulo comercial y su extensión de la comparación (ADR-012, DP-1 opción B).

`ExtensionComercial` cumple el puerto `comparacion.domain.extensiones.ExtensionComparacion`: la
comparación la consulta por el registro de `core` y nunca importa este módulo. Solo entrega
precios y promociones de comercios VERIFICADOS (ADR-015); nada del usuario dueño del perfil
(M-15).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.comparacion.domain.extensiones import (
    DatosComerciales,
    PrecioOficialVigente,
    PromocionComparacion,
)
from apps.comparacion.domain.oficial import DIAS_DISCREPANCIA, discrepancia
from apps.comparacion.domain.tarjeta import formatear_pesos
from apps.precios.models import ReportePrecio
from apps.precios.selectors import politica_vigencia

from .domain.promociones import Promocion as PromocionDominio
from .domain.promociones import Vigencia, estrategia_de, precio_efectivo_por_unidad
from .models import PerfilComercio, PrecioOficial, Promocion, SolicitudCorreccion

ACTIVOS = ~Q(estado=PerfilComercio.Estado.RECHAZADO)


# ---------- Perfil ----------


def perfil_de(usuario) -> PerfilComercio | None:
    """El perfil activo (pendiente o verificado) de la persona, o None."""
    if not getattr(usuario, "is_authenticated", False):
        return None
    return (
        PerfilComercio.objects.filter(ACTIVOS, usuario=usuario)
        .select_related("establecimiento")
        .first()
    )


def ultimo_rechazo(usuario) -> PerfilComercio | None:
    if not getattr(usuario, "is_authenticated", False):
        return None
    return (
        PerfilComercio.objects.filter(usuario=usuario, estado=PerfilComercio.Estado.RECHAZADO)
        .select_related("establecimiento")
        .order_by("-verificado_en")
        .first()
    )


def establecimiento_tiene_perfil(establecimiento_id: int) -> bool:
    return PerfilComercio.objects.filter(ACTIVOS, establecimiento_id=establecimiento_id).exists()


# ---------- Domain ↔ modelo ----------


def promocion_de_dominio(promocion: Promocion, precio_regular) -> PromocionDominio:
    estrategia = estrategia_de(
        promocion.tipo,
        porcentaje=promocion.porcentaje,
        precio_especial=promocion.precio_especial,
        pague=promocion.pague,
        lleve=promocion.lleve,
    )
    return PromocionDominio(
        estrategia=estrategia,
        precio_regular=precio_regular,
        vigencia=Vigencia(promocion.inicio, promocion.fin),
    )


# ---------- Portal ----------


@dataclass(frozen=True)
class PrecioDelPortal:
    precio: PrecioOficial
    vigente: bool
    vence_en: datetime
    usuarios_reportan: str  # «$5.200» si hay discrepancia (ADR-018); vacío si no

    @property
    def precio_texto(self) -> str:
        return formatear_pesos(self.precio.precio)


def _reportes_recientes(perfil: PerfilComercio, presentacion_ids, ahora) -> dict[int, list]:
    """(precio, fecha) de los reportes publicados de su tienda en 7 días, en un solo query."""
    filas = ReportePrecio.objects.filter(
        establecimiento_id=perfil.establecimiento_id,
        presentacion_id__in=presentacion_ids,
        estado=ReportePrecio.Estado.PUBLICADO,
        fecha_observacion__gte=ahora - timedelta(days=DIAS_DISCREPANCIA),
    ).values_list("presentacion_id", "precio", "fecha_observacion")
    agrupados: dict[int, list] = {}
    for presentacion_id, precio, fecha in filas:
        agrupados.setdefault(presentacion_id, []).append((precio, fecha))
    return agrupados


def precios_del_portal(perfil: PerfilComercio) -> list[PrecioDelPortal]:
    """Sus precios oficiales con vigencia y el aviso de discrepancia del ADR-018."""
    ahora = timezone.now()
    precios = list(
        perfil.precios.select_related("presentacion__producto__marca").order_by(
            "presentacion__producto__nombre", "presentacion__cantidad"
        )
    )
    reportes = _reportes_recientes(perfil, [p.presentacion_id for p in precios], ahora)
    ventana = timedelta(days=politica_vigencia().dias_oficial)  # ADR-003: 30 días
    resultado = []
    for p in precios:
        aviso = discrepancia(p.precio, reportes.get(p.presentacion_id, []), ahora)
        resultado.append(
            PrecioDelPortal(
                precio=p,
                vigente=ahora - p.confirmado_en <= ventana,
                vence_en=p.confirmado_en + ventana,
                usuarios_reportan=formatear_pesos(aviso) if aviso is not None else "",
            )
        )
    return resultado


def promociones_del_portal(perfil: PerfilComercio, limite: int = 50) -> list[dict]:
    ahora = timezone.now()
    regulares = dict(perfil.precios.values_list("presentacion_id", "precio"))
    filas = []
    for p in perfil.promociones.select_related("presentacion__producto").order_by("-creado_en")[
        :limite
    ]:
        regular = regulares.get(p.presentacion_id)
        dominio = promocion_de_dominio(p, regular) if regular else None
        filas.append(
            {
                "promocion": p,
                "descripcion": dominio.estrategia.describir() if dominio else p.get_tipo_display(),
                "precio_efectivo": formatear_pesos(dominio.precio_efectivo()) if dominio else "",
                "vigente": p.activa and p.inicio <= ahora < p.fin and dominio is not None,
            }
        )
    return filas


def correcciones_del_perfil(perfil: PerfilComercio, limite: int = 20):
    return list(perfil.correcciones.select_related("reporte__presentacion").order_by("-creado_en"))[
        :limite
    ]


def reportes_de_su_tienda(perfil: PerfilComercio, limite: int = 30):
    """Precios reportados por usuarios en su tienda, para pedir una corrección (RF-C06).

    Sin autor (M-15): el comercio ve el precio, no quién lo reportó.
    """
    return list(
        ReportePrecio.objects.filter(
            establecimiento_id=perfil.establecimiento_id, estado=ReportePrecio.Estado.PUBLICADO
        )
        .select_related("presentacion__producto")
        .only("pk", "precio", "fecha_observacion", "presentacion")
        .order_by("-fecha_observacion")[:limite]
    )


# ---------- Bandeja de moderación ----------


def perfiles_pendientes(limite: int = 50):
    return list(
        PerfilComercio.objects.filter(estado=PerfilComercio.Estado.PENDIENTE)
        .select_related("establecimiento", "usuario")
        .order_by("creado_en")[:limite]
    )


def correcciones_pendientes(limite: int = 50):
    return list(
        SolicitudCorreccion.objects.filter(estado=SolicitudCorreccion.Estado.PENDIENTE)
        .select_related("perfil__establecimiento", "reporte__presentacion")
        .order_by("creado_en")[:limite]
    )


# ---------- Extensión de la comparación (puerto del ADR-012) ----------


def _oficiales_verificados(producto_ids: Sequence[int]):
    return PrecioOficial.objects.filter(
        perfil__estado=PerfilComercio.Estado.VERIFICADO,
        presentacion__producto_id__in=producto_ids,
    ).select_related("presentacion", "perfil")


def _promocion_para_comparar(p: Promocion, regular, presentacion) -> PromocionComparacion:
    dominio = promocion_de_dominio(p, regular)
    unitario, base = precio_efectivo_por_unidad(dominio, presentacion.cantidad, presentacion.unidad)
    return PromocionComparacion(
        producto_id=presentacion.producto_id,
        establecimiento_id=p.perfil.establecimiento_id,
        presentacion_id=p.presentacion_id,
        tipo=p.tipo,
        descripcion=dominio.estrategia.describir(),
        precio_efectivo=dominio.precio_efectivo(),
        precio_efectivo_unitario=unitario,
        unidad_base=base.value,
        inicio=p.inicio,
        fin=p.fin,
        motivo=p.get_motivo_display(),
        condiciones=p.condiciones,
        fecha_vencimiento_producto=p.fecha_vencimiento_producto,
    )


def datos_comerciales(producto_ids: Sequence[int], ahora: datetime) -> DatosComerciales:
    """Precios oficiales y promociones vigentes de comercios verificados, en dos queries."""
    oficiales = list(_oficiales_verificados(producto_ids))
    regulares = {(o.perfil_id, o.presentacion_id): o for o in oficiales}
    promociones = Promocion.objects.filter(
        activa=True,
        inicio__lte=ahora,
        fin__gt=ahora,
        perfil__estado=PerfilComercio.Estado.VERIFICADO,
        presentacion__producto_id__in=producto_ids,
    ).select_related("perfil", "presentacion")
    promos = []
    for p in promociones:
        oficial = regulares.get((p.perfil_id, p.presentacion_id))
        if oficial is not None:  # sin precio regular no hay precio efectivo que mostrar
            promos.append(_promocion_para_comparar(p, oficial.precio, p.presentacion))
    return DatosComerciales(
        oficiales=tuple(
            PrecioOficialVigente(
                producto_id=o.presentacion.producto_id,
                establecimiento_id=o.perfil.establecimiento_id,
                presentacion_id=o.presentacion_id,
                precio=o.precio,
                confirmado_en=o.confirmado_en,
            )
            for o in oficiales
        ),
        promociones=tuple(promos),
    )


class ExtensionComercial:
    """Adaptador del puerto `ExtensionComparacion` (lo registra `ComerciosConfig.ready`)."""

    def datos_para(self, producto_ids: Sequence[int], ahora: datetime) -> DatosComerciales:
        return datos_comerciales(producto_ids, ahora)


EXTENSION = ExtensionComercial()
