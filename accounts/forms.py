from django import forms
from django.contrib.auth import get_user_model
from .models import User

from .models import Profile

User = get_user_model()

PAIS_CHOICES = [
    ("", "— Selecciona —"),
    ("CL", "Chile"),
    ("AR", "Argentina"),
    ("PE", "Perú"),
    ("BR", "Brasil"),
    ("US", "Estados Unidos"),
    ("OTRO", "Otro"),
]

TIPO_DOC_CHOICES = [
    ("RUT", "RUT"),
    ("Pasaporte", "Pasaporte"),
]


class SignupForm(forms.Form):
    # Nombres / apellidos
    nombres = forms.CharField(label="Nombres", max_length=150)
    apellido1 = forms.CharField(label="Apellido paterno", max_length=150)
    apellido2 = forms.CharField(
        label="Apellido materno", max_length=150, required=False
    )

    # Documento
    tipo_doc = forms.ChoiceField(label="Tipo doc.", choices=TIPO_DOC_CHOICES)
    numero_documento = forms.CharField(label="Número documento", max_length=50)

    # Email
    email = forms.EmailField(label="Email")
    email2 = forms.EmailField(label="Confirmar email")

    # Teléfono
    telefono_movil = forms.CharField(
        label="Teléfono móvil",
        min_length=8,
        help_text="Solo números, al menos 8 dígitos.",
    )

    # Ubicación
    pais = forms.ChoiceField(label="País", choices=PAIS_CHOICES)
    ciudad = forms.CharField(label="Ciudad", max_length=100)
    comuna = forms.CharField(label="Comuna", max_length=100)
    region = forms.CharField(label="Región", max_length=100, required=False)

    # Empresa
    empresa = forms.CharField(label="Empresa / Institución", max_length=200)
    cargo = forms.CharField(label="Cargo", max_length=200)
    rubro = forms.CharField(label="Rubro", max_length=200)

    # Password
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        min_length=6,
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput,
        min_length=6,
    )

    # Checks
    acepta_terminos = forms.BooleanField(
        label=(
            "Acepto los Términos y Condiciones y autorizo el tratamiento "
            "de mis datos personales según la Política de Privacidad."
        )
    )
    recibe_novedades = forms.BooleanField(
        label="Deseo recibir noticias y beneficios de [NOMBRE-SITIO] y sus eventos asociados.",
        required=False,
    )

    # Validaciones
    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Ya existe un usuario registrado con este email."
            )
        return email

    def clean(self):
        cleaned = super().clean()

        email = cleaned.get("email")
        email2 = cleaned.get("email2")
        if email and email2 and email.lower() != email2.lower():
            self.add_error("email2", "Los emails no coinciden.")

        pwd = cleaned.get("password")
        pwd2 = cleaned.get("password2")
        if pwd and pwd2 and pwd != pwd2:
            self.add_error("password2", "Las contraseñas no coinciden.")

        return cleaned


class ProfileForm(forms.ModelForm):
    # Campos extra SOLO para cambiar la contraseña (opcionales)
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        required=False,
        min_length=6,
    )
    new_password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput,
        required=False,
        min_length=6,
    )

    class Meta:
        model = Profile
        fields = [
            "nombres",
            "apellido1",
            "apellido2",
            "telefono_movil",
            "pais",
            "region",
            "ciudad",
            "comuna",
            "empresa",
            "cargo",
            "rubro",
            "recibe_novedades",
        ]

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")

        # Si el usuario quiere cambiar contraseña, deben coincidir
        if p1 or p2:
            if p1 != p2:
                self.add_error("new_password2", "Las contraseñas no coinciden.")
        return cleaned
    

class EditarAdminForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=150, required=False)
    password1 = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        required=False,
    )
    password2 = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput,
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")

        if p1 or p2:
            if p1 != p2:
                raise forms.ValidationError("Las contraseñas no coinciden.")
            if len(p1) < 6:
                raise forms.ValidationError("La contraseña debe tener al menos 6 caracteres.")

        return cleaned
    

class AsignarAdminForm(forms.Form):
    nombre = forms.CharField(label="Nombre", max_length=150)
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    confirm_password = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("confirm_password")

        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")

        return cleaned


class EditarAdminForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    password = forms.CharField(
        label="Nueva contraseña",
        required=False,  # vacío = no cambiar
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        help_text="Déjala en blanco si no quieres cambiarla.",
    )