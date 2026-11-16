from .models import Usuario


def existe_usuario(username: str) -> bool:
    return Usuario.objects.filter(username__iexact=username).exists()


def existe_otro_usuario(username: str, *, excepto_id: int) -> bool:
    return Usuario.objects.filter(username__iexact=username).exclude(pk=excepto_id).exists()


def es_cuenta_desactivada(*, username: str, password: str) -> bool:
    """True si existe una cuenta desactivada con esas credenciales correctas.

    Solo se confirma con la contraseña correcta: no revela qué usuarios existen.
    """
    usuario = Usuario.objects.filter(username__iexact=username, is_active=False).first()
    return usuario is not None and usuario.check_password(password)
