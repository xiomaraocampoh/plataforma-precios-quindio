from apps.integraciones import services as integraciones


def asistente(request) -> dict:
    """Para el botón flotante de todas las páginas: ¿K-nasta está usando IA?"""
    return {"asistente_ia": integraciones.asistente_ia_activo()}
