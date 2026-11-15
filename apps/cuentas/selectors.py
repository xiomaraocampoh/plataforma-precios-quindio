from .models import Usuario


def existe_usuario(username: str) -> bool:
    return Usuario.objects.filter(username__iexact=username).exists()
