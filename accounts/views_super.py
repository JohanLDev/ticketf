from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Cuenta, UsuarioRol, User
from django import forms
from .models import Cuenta, UsuarioRol, User
from .forms import EditarAdminForm


is_super = user_passes_test(lambda u: u.is_authenticated and u.is_superuser)

class CuentaForm(forms.ModelForm):
    class Meta:
        model = Cuenta
        fields = ["nombre", "rut", "razon_social", "plan", "estado"]

@login_required
@is_super
def super_cuentas(request):
    return render(request, "super/cuentas_list.html", {"cuentas": Cuenta.objects.all()})

@login_required
@is_super
def super_crear_cuenta(request):
    form = CuentaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("accounts:super_cuentas")
    return render(request, "super/cuenta_form.html", {"form": form})

class AsignarAdminForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=True,
    )
    confirm_password = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=True,
    )

    def clean(self):
        cleaned = super().clean()
        pwd = cleaned.get("password")
        cpwd = cleaned.get("confirm_password")

        if pwd and cpwd and pwd != cpwd:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned



class AsignarAdminForm(forms.Form):
    nombre = forms.CharField(
        label="Nombre",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=True,
    )
    confirm_password = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
        required=True,
    )

    def clean(self):
        cleaned = super().clean()
        pwd = cleaned.get("password")
        cpwd = cleaned.get("confirm_password")

        if pwd and cpwd and pwd != cpwd:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned

@login_required
@is_super
def super_asignar_admin(request, cuenta_id):
    cuenta = get_object_or_404(Cuenta, id=cuenta_id)

    if request.method == "POST":
        form = AsignarAdminForm(request.POST)
        if form.is_valid():
            nombre = form.cleaned_data["nombre"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            user, created = User.objects.get_or_create(
                email=email,
                defaults={"first_name": nombre},
            )

            if not created and not user.first_name:
                user.first_name = nombre

            user.is_staff = True

            if password:
                user.set_password(password)

            user.save()

            rol, created_rol = UsuarioRol.objects.get_or_create(
                usuario=user,
                cuenta=cuenta,
                defaults={"rol": "admin", "activo": True},
            )

            if not created_rol:
                rol.rol = "admin"
                rol.activo = True
                rol.save()

            messages.success(
                request,
                f"{email} ahora es ADMIN de la cuenta {cuenta.nombre}."
            )
            return redirect("accounts:ver_admins", cuenta_id=cuenta.id)
    else:
        form = AsignarAdminForm()

    context = {"cuenta": cuenta, "form": form}
    return render(request, "super/asignar_admin.html", context)



@login_required
@is_super
def ver_admins(request, cuenta_id):
    cuenta = get_object_or_404(Cuenta, pk=cuenta_id)

    admins = UsuarioRol.objects.filter(
        cuenta=cuenta,
        rol="admin",
        activo=True
    ).select_related("usuario")

    context = {
        "cuenta": cuenta,
        "admins": admins,
    }

    return render(request, "super/ver_admins.html", context)


@login_required
@is_super
def eliminar_admin(request, cuenta_id, rol_id):
    cuenta = get_object_or_404(Cuenta, pk=cuenta_id)

    rol = get_object_or_404(
        UsuarioRol,
        pk=rol_id,
        cuenta=cuenta,
        rol="admin",
    )

    if request.method == "POST":
        rol.delete()
        messages.success(
            request,
            f"Se quitó el admin '{rol.usuario.email}' de la cuenta {cuenta.nombre}."
        )
        return redirect("accounts:ver_admins", cuenta_id=cuenta.id)

    return redirect("accounts:ver_admins", cuenta_id=cuenta.id)


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.is_superuser)
def editar_admin(request, cuenta_id, rol_id):
    # 1. Traer la cuenta
    cuenta = get_object_or_404(Cuenta, id=cuenta_id)

    # 2. Traer el rol (NO al user directo)
    rol = get_object_or_404(
        UsuarioRol,
        id=rol_id,
        cuenta=cuenta,
        rol="admin",
        activo=True,
    )

    # 3. Usuario asociado a ese rol
    user = rol.usuario

    if request.method == "POST":
        form = EditarAdminForm(request.POST)
        if form.is_valid():
            # actualizar nombre
            user.first_name = form.cleaned_data["nombre"]

            # si viene contraseña nueva, la cambiamos
            nueva_password = form.cleaned_data.get("password")
            if nueva_password:
                user.set_password(nueva_password)

            user.save()
            messages.success(request, "Admin actualizado correctamente.")
            return redirect("accounts:ver_admins", cuenta_id=cuenta.id)
    else:
        # inicializamos el formulario con el nombre actual
        form = EditarAdminForm(initial={"nombre": user.first_name})

    context = {
        "cuenta": cuenta,
        "admin": user,
        "form": form,
    }
    return render(request, "super/editar_admin.html", context)


@login_required
@is_super
def super_editar_cuenta(request, cuenta_id):
    # cuenta_id es UUID
    cuenta = get_object_or_404(Cuenta, id=cuenta_id)

    if request.method == "POST":
        form = CuentaForm(request.POST, instance=cuenta)
        if form.is_valid():
            form.save()
            messages.success(request, "Cuenta actualizada correctamente.")
            return redirect("accounts:super_cuentas")
    else:
        form = CuentaForm(instance=cuenta)

    context = {
        "form": form,
        "cuenta": cuenta,
        "modo": "editar",
    }
    return render(request, "super/cuenta_form.html", context)


@login_required
@is_super
def super_eliminar_cuenta(request, cuenta_id):
    # cuenta_id es UUID
    cuenta = get_object_or_404(Cuenta, id=cuenta_id)

    if request.method == "POST":
        nombre = cuenta.nombre
        cuenta.delete()
        messages.success(
            request,
            f"La cuenta '{nombre}' fue eliminada correctamente."
        )
        return redirect("accounts:super_cuentas")

    return render(request, "super/cuenta_delete_confirm.html", {"cuenta": cuenta})
