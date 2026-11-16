import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password

from . import selectors
from .models import Usuario

FORMATO_USUARIO = re.compile(r"[\w.-]{3,30}")  # letras (con tildes y ñ), números, . - _
ERROR_FORMATO_USUARIO = (
    "Usa de 3 a 30 caracteres: letras, números, punto, guion o guion bajo, sin espacios."
)
ERROR_USUARIO_REPETIDO = "Ya existe un usuario con ese nombre. Prueba con otro."
AYUDA_USUARIO = (
    "De 3 a 30 caracteres: letras, números, punto, guion o guion bajo, sin espacios. "
    "No se muestra en tus reportes."
)


def _usuario_con_formato(valor: str) -> str:
    valor = valor.strip()
    if not FORMATO_USUARIO.fullmatch(valor):
        raise forms.ValidationError(ERROR_FORMATO_USUARIO)
    return valor


def _campo_usuario() -> forms.CharField:
    return forms.CharField(
        label="Nombre de usuario",
        help_text=AYUDA_USUARIO,
        error_messages={"required": "Escribe tu nombre de usuario."},
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "autocorrect": "off",
                "spellcheck": "false",
                "maxlength": "30",
            }
        ),
    )


class RegistroForm(forms.Form):
    username = _campo_usuario()
    email = forms.EmailField(
        label="Correo electrónico",
        required=False,
        error_messages={"invalid": "Escribe un correo válido, por ejemplo nombre@correo.com."},
        help_text="Solo sirve para recuperar tu contraseña. No se publica.",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "inputmode": "email"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        strip=False,
        error_messages={"required": "Escribe una contraseña."},
        help_text="Evita claves comunes y que se parezca a tu nombre de usuario.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Repite la contraseña",
        strip=False,
        error_messages={"required": "Repite la contraseña para confirmarla."},
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    acepto_tratamiento_datos = forms.BooleanField(
        label="Autorizo el tratamiento de mis datos personales (Ley 1581 de 2012)",
        error_messages={
            "required": (
                "Para crear la cuenta necesitamos tu autorización de tratamiento de datos "
                "(Ley 1581 de 2012)."
            )
        },
    )

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = _usuario_con_formato(self.cleaned_data["username"])
        if selectors.existe_usuario(username):
            raise forms.ValidationError(ERROR_USUARIO_REPETIDO)
        return username

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1:  # se valida siempre: así la persona ve todos los problemas de una vez
            candidato = Usuario(username=datos.get("username", ""), email=datos.get("email", ""))
            try:
                validate_password(p1, candidato)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden. Escríbelas de nuevo.")
        return datos


class IngresarForm(AuthenticationForm):
    """Ingreso con mensajes claros y en el mismo tono que el resto de la plataforma."""

    error_messages = {
        "invalid_login": (
            "El usuario o la contraseña no son correctos. Revísalos e inténtalo de nuevo; "
            "la contraseña distingue mayúsculas y minúsculas."
        ),
        "inactive": (
            "Esta cuenta está desactivada. Si crees que es un error, "
            "comunícate con el equipo de AhorraPues."
        ),
    }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
        usuario, clave = self.fields["username"], self.fields["password"]
        usuario.label = "Nombre de usuario"
        usuario.error_messages["required"] = "Escribe tu nombre de usuario."
        usuario.widget.attrs.update(
            {"autocapitalize": "none", "autocorrect": "off", "spellcheck": "false"}
        )
        clave.label = "Contraseña"
        clave.error_messages["required"] = "Escribe tu contraseña."

    def get_invalid_login_error(self):
        # El sistema de acceso rechaza a los inactivos como si la clave fuera incorrecta; si la
        # contraseña SÍ es correcta, decimos la verdad para que no siga probando claves.
        if selectors.es_cuenta_desactivada(
            username=self.cleaned_data.get("username", ""),
            password=self.cleaned_data.get("password", ""),
        ):
            return forms.ValidationError(self.error_messages["inactive"], code="inactive")
        return super().get_invalid_login_error()


class DatosForm(forms.Form):
    """RF-03: datos que el titular puede ver y actualizar."""

    username = _campo_usuario()
    email = forms.EmailField(
        label="Correo electrónico",
        required=False,
        error_messages={"invalid": "Escribe un correo válido, por ejemplo nombre@correo.com."},
        help_text="Solo para recuperar tu contraseña. No se publica.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_username(self):
        username = _usuario_con_formato(self.cleaned_data["username"])
        if selectors.existe_otro_usuario(username, excepto_id=self.usuario.pk):
            raise forms.ValidationError(ERROR_USUARIO_REPETIDO)
        return username


class SuprimirCuentaForm(forms.Form):
    """RF-03: la supresión exige la contraseña actual y una confirmación expresa."""

    password = forms.CharField(
        label="Tu contraseña actual",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )
    confirmo = forms.BooleanField(
        label="Entiendo que la supresión no se puede deshacer",
        error_messages={"required": "Marca la casilla para confirmar."},
    )

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.usuario.check_password(password):
            raise forms.ValidationError("La contraseña no es correcta.")
        return password


# ---------- Verificación en dos pasos y preferencias (RF-27) ----------

_CODIGO = {
    "inputmode": "numeric",
    "autocomplete": "one-time-code",
    "pattern": "[0-9 ]*",
    "maxlength": "7",
    "class": "campo-codigo",
}


class CodigoForm(forms.Form):
    """Código de 6 dígitos (correo o app) o, si no hay celular, un código de respaldo."""

    codigo = forms.CharField(
        label="Código de 6 dígitos",
        required=False,
        max_length=7,
        widget=forms.TextInput(attrs=_CODIGO),
    )
    respaldo = forms.CharField(
        label="Código de respaldo",
        required=False,
        max_length=12,
        help_text="Uno de los 10 códigos que guardaste (abcd-efgh). Cada uno sirve una vez.",
        widget=forms.TextInput(attrs={"autocomplete": "off", "autocapitalize": "off"}),
    )
    confiar = forms.BooleanField(label="Confiar en este dispositivo 30 días", required=False)

    def clean(self):
        datos = super().clean()
        codigo = "".join((datos.get("codigo") or "").split())
        respaldo = (datos.get("respaldo") or "").strip()
        if not codigo and not respaldo:
            raise forms.ValidationError("Escribe el código de 6 dígitos o un código de respaldo.")
        if codigo and (len(codigo) != 6 or not codigo.isdigit()):
            self.add_error("codigo", "El código tiene 6 dígitos.")
        datos["valor"] = respaldo or codigo
        return datos


class ContrasenaActualForm(forms.Form):
    """Las acciones de seguridad piden la contraseña actual (RF-27)."""

    password = forms.CharField(
        label="Tu contraseña actual",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.usuario.check_password(password):
            raise forms.ValidationError("La contraseña no es correcta.")
        return password


class ActivarAppForm(ContrasenaActualForm):
    codigo = forms.CharField(
        label="Código que muestra la app", max_length=7, widget=forms.TextInput(attrs=_CODIGO)
    )


class PrimerCodigoAppForm(forms.Form):
    """Al ingresar sin método configurado (rol con 2FA obligatoria): la contraseña ya se pidió."""

    codigo = forms.CharField(
        label="Código que muestra la app", max_length=7, widget=forms.TextInput(attrs=_CODIGO)
    )


class PreferenciasForm(forms.Form):
    correos_informativos = forms.BooleanField(
        label="Recibir correos informativos (bienvenida y resultados de moderación)",
        required=False,
        help_text="Los correos de seguridad (códigos, cambios de contraseña, ingresos nuevos) "
        "siempre llegan: protegen tu cuenta.",
    )
