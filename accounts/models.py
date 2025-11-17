# accounts/models.py
import uuid
from django.db import models
from django.conf import settings
from django.contrib.auth.models import BaseUserManager, AbstractUser

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)
    

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.email
    

class Cuenta(models.Model):
    """Empresa o productora (tenant)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=20, blank=True, null=True)
    razon_social = models.CharField(max_length=200, blank=True, null=True)
    plan = models.CharField(
        max_length=20,
        choices=[("basico", "Básico"), ("premium", "Premium")],
        default="basico",
    )
    estado = models.CharField(
        max_length=20,
        choices=[("activa", "Activa"), ("suspendida", "Suspendida")],
        default="activa",
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class UsuarioRol(models.Model):
    """Asocia usuarios con cuentas y define su rol dentro de la cuenta"""
    ROLES = [
        ("superadmin", "Super Admin"),
        ("admin", "Admin"),
        ("staff", "Staff"),
        ("customer", "Usuario"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name="usuarios")
    rol = models.CharField(max_length=20, choices=ROLES, default="customer")
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("usuario", "cuenta")

    def __str__(self):
        return f"{self.usuario.email} → {self.rol} ({self.cuenta.nombre})"
    

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Datos personales
    nombres = models.CharField(max_length=150)
    apellido1 = models.CharField("Apellido paterno", max_length=150)
    apellido2 = models.CharField("Apellido materno", max_length=150, blank=True)

    # Documento
    tipo_doc = models.CharField(max_length=20, blank=True)  # "RUT" / "Pasaporte"
    numero_documento = models.CharField(max_length=50, blank=True)

    # Contacto
    telefono_movil = models.CharField(max_length=30)
    pais = models.CharField(max_length=2, default="CL")
    region = models.CharField(max_length=100, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    comuna = models.CharField(max_length=100, blank=True)

    # Empresa
    empresa = models.CharField(max_length=200, blank=True)
    cargo = models.CharField(max_length=200, blank=True)
    rubro = models.CharField(max_length=200, blank=True)

    # Preferencias
    acepta_terminos = models.BooleanField(default=False)
    recibe_novedades = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nombres} {self.apellido1} ({self.user.email})"

