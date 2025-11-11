from django.contrib import admin
from .models import User, Cuenta, UsuarioRol

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "first_name", "last_name", "is_staff", "is_superuser")
    search_fields = ("email",)

@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "plan", "estado", "creada_en")
    search_fields = ("nombre",)

@admin.register(UsuarioRol)
class UsuarioRolAdmin(admin.ModelAdmin):
    list_display = ("usuario", "cuenta", "rol", "activo", "creado_en")
    list_filter = ("rol", "activo")
