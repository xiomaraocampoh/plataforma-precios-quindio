from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuario personalizado desde el día 1 (cambiarlo después exige migraciones costosas)."""

    class Rol(models.TextChoices):
        # Los valores coinciden con apps.cuentas.domain.roles.Rol (más «comercio», Corte III)
        REPORTANTE = "reportante", "Reportante"
        COMERCIO = "comercio", "Comercio"
        MODERADOR = "moderador", "Moderador"
        EDITOR_CATALOGO = "editor_catalogo", "Editor de catálogo"
        ADMINISTRADOR = "administrador", "Administrador"

    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.REPORTANTE)
    # Ley 1581 de 2012: autorización expresa del titular
    acepto_tratamiento_datos = models.BooleanField(default=False)
    fecha_aceptacion_datos = models.DateTimeField(null=True, blank=True)
    # RF-03: fecha en que el titular suprimió su cuenta (los aportes quedan anonimizados)
    suprimido_en = models.DateTimeField(null=True, blank=True)
    # RF-24: el correo se confirma con un enlace firmado; sin confirmar no hay informativos
    email_verificado_en = models.DateTimeField(null=True, blank=True)
    # RF-27 / Ley 1581: los correos informativos se pueden apagar; los de seguridad, no
    correos_informativos = models.BooleanField(default=True)

    class Meta:
        permissions = [("gestionar_cuentas", "Asignar roles y activar o suspender cuentas")]

    def __str__(self) -> str:
        return self.username


class SegundoFactor(models.Model):
    """Verificación en dos pasos de una cuenta (RF-27, ADR-021).

    De los códigos por correo solo se guarda el HMAC. El secreto TOTP sí se guarda (sin él no se
    puede verificar la app autenticadora); ver ADR-021, «Riesgos».
    """

    class Metodo(models.TextChoices):
        NINGUNO = "ninguno", "Sin verificación en dos pasos"
        CORREO = "correo", "Código por correo"
        APP = "app", "App autenticadora"

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="segundo_factor")
    metodo = models.CharField(max_length=10, choices=Metodo.choices, default=Metodo.NINGUNO)
    totp_secreto = models.CharField(max_length=64, blank=True)
    totp_ultimo_paso = models.BigIntegerField(null=True, blank=True)  # un código TOTP, un uso
    codigo_hash = models.CharField(max_length=64, blank=True)
    codigo_vence_en = models.DateTimeField(null=True, blank=True)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    # Al subirla se invalidan todas las cookies de «confiar en este dispositivo»
    version_confianza = models.PositiveIntegerField(default=1)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"2FA de {self.usuario} ({self.metodo})"


class CodigoRespaldo(models.Model):
    """Código de respaldo de un solo uso. Solo se guarda su hash."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="codigos_respaldo")
    codigo_hash = models.CharField(max_length=64)
    usado_en = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return (
            f"Código de respaldo de {self.usuario} ({'usado' if self.usado_en else 'disponible'})"
        )


class DispositivoConocido(models.Model):
    """Huella (HMAC de navegador + red /24) de un dispositivo con el que ya se ingresó (RF-25).
    Nunca se guarda la IP completa."""

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="dispositivos")
    huella = models.CharField(max_length=64)
    navegador = models.CharField(max_length=60)
    creado_en = models.DateTimeField(auto_now_add=True)
    visto_en = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["usuario", "huella"], name="dispositivo_unico")
        ]

    def __str__(self) -> str:
        return f"{self.navegador} de {self.usuario}"
