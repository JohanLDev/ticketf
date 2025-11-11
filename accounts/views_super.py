from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Cuenta, UsuarioRol, User

is_super = user_passes_test(lambda u: u.is_superuser)

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
    email = forms.EmailField()

@login_required
@is_super
def super_asignar_admin(request, cuenta_id):
    cuenta = get_object_or_404(Cuenta, pk=cuenta_id)
    form = AsignarAdminForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user, _ = User.objects.get_or_create(email=email, defaults={"is_active": True})
        UsuarioRol.objects.update_or_create(
            usuario=user, cuenta=cuenta, defaults={"rol": "admin", "activo": True}
        )
        return redirect("accounts:super_cuentas")
    return render(request, "super/asignar_admin.html", {"form": form, "cuenta": cuenta})
