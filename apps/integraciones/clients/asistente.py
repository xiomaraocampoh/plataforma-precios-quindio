"""Adaptador de K-nasta, el asistente de compras, con la API de Anthropic (ADR-0030).

Puerto/adaptador, como el reconocimiento por foto: el resto del sistema depende de
`ModeloConversacional`. El adaptador hace UNA llamada con herramientas y devuelve los bloques tal
como llegaron; el bucle de herramientas y las cifras viven en `apps/canasta`. Garantías:
- Timeout obligatorio; toda falla del servicio externo se traduce a `AsistenteNoDisponibleError`
  y K-nasta sigue en modo básico (reglas).
- Las herramientas son de solo lectura; el modelo no puede escribir en la base ni abrir URLs.
- Las imágenes viajan en la petición y no se guardan.
"""

import base64
import logging
from dataclasses import dataclass
from typing import Protocol

import anthropic
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_TOKENS = 1024


class AsistenteNoDisponibleError(RuntimeError):
    """El asistente con IA no está configurado o no respondió a tiempo."""


@dataclass(frozen=True)
class RespuestaModelo:
    parada: str  # end_turn | tool_use | refusal | max_tokens | ...
    bloques: list[dict]  # los bloques de contenido, tal como llegaron (se reenvían con tool_use)

    @property
    def texto(self) -> str:
        return "".join(b.get("text", "") for b in self.bloques if b.get("type") == "text").strip()

    @property
    def llamadas(self) -> list[dict]:
        return [b for b in self.bloques if b.get("type") == "tool_use"]


class ModeloConversacional(Protocol):
    def responder(
        self, *, sistema: str, mensajes: list[dict], herramientas: list[dict]
    ) -> RespuestaModelo: ...


def bloque_imagen(imagen: bytes, tipo: str) -> dict:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": tipo,
            "data": base64.standard_b64encode(imagen).decode(),
        },
    }


class AsistenteClaude:
    def __init__(self, *, cliente=None, modelo: str | None = None):
        self._cliente = cliente
        self._modelo = modelo or settings.INTEGRACIONES["ASISTENTE_MODELO"]

    def _cliente_listo(self):
        if self._cliente is None:
            cfg = settings.INTEGRACIONES
            if not cfg["ANTHROPIC_API_KEY"]:
                raise AsistenteNoDisponibleError("Falta ANTHROPIC_API_KEY.")
            self._cliente = anthropic.Anthropic(
                api_key=cfg["ANTHROPIC_API_KEY"],
                timeout=float(cfg["ASISTENTE_TIMEOUT_S"]),
                max_retries=1,
            )
        return self._cliente

    def responder(
        self, *, sistema: str, mensajes: list[dict], herramientas: list[dict]
    ) -> RespuestaModelo:
        try:
            respuesta = self._cliente_listo().messages.create(
                model=self._modelo,
                max_tokens=MAX_TOKENS,
                system=sistema,
                tools=herramientas,
                tool_choice={"type": "auto"},  # forzar una herramienta falla en Opus/Sonnet 5.5
                output_config={"effort": "low"},
                messages=mensajes,
            )
        except anthropic.APIError as exc:  # red, tiempo, límite, clave inválida, etc.
            logger.warning("Asistente no disponible: %s", type(exc).__name__)
            raise AsistenteNoDisponibleError(type(exc).__name__) from exc
        return RespuestaModelo(
            parada=respuesta.stop_reason or "",
            bloques=[b.model_dump(exclude_none=True) for b in respuesta.content],
        )
