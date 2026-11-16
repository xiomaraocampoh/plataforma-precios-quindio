from .models import Usuario


def existe_usuario(username: str) -> bool:
    return Usuario.objects.filter(username__iexact=username).exists()


def existe_otro_usuario(username: str, *, excepto_id: int) -> bool:
    return Usuario.objects.filter(username__iexact=username).exclude(pk=excepto_id).exists()
