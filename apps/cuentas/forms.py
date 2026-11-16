from django import forms
from django.contrib.auth.password_validation import validate_password

from . import selectors


class RegistroForm(forms.Form):
    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        help_text="Se usa para ingresar. No se muestra en tus reportes.",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autocapitalize": "none"}),
    )
    email = forms.EmailField(
        label="Correo electrónico (opcional)",
        required=False,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    password1 = forms.CharField(
        label="Contraseña",
        strip=False,
        help_text="Mínimo 8 caracteres; evita claves comunes o solo números.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Repite la contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    acepto_tratamiento_datos = forms.BooleanField(
        label="Autorizo el tratamiento de mis datos personales (Ley 1581 de 2012)",
        error_messages={"required": "Necesitamos tu autorización para crear la cuenta."},
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if selectors.existe_usuario(username):
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
        return username

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 and p2:
            if p1 != p2:
                self.add_error("password2", "Las contraseñas no coinciden.")
            else:
                try:
                    validate_password(p1)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return datos


class DatosForm(forms.Form):
    """RF-03: datos que el titular puede ver y actualizar."""

    username = forms.CharField(
        label="Nombre de usuario",
        max_length=150,
        help_text="Se usa para ingresar. No se muestra en tus reportes.",
        widget=forms.TextInput(attrs={"autocomplete": "username", "autocapitalize": "none"}),
    )
    email = forms.EmailField(
        label="Correo electrónico",
        required=False,
        help_text="Solo para recuperar tu contraseña. No se publica.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if selectors.existe_otro_usuario(username, excepto_id=self.usuario.pk):
            raise forms.ValidationError("Ya existe un usuario con ese nombre.")
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
