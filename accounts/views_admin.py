from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Cuenta
from .utils import get_current_cuenta, require_role

@login_required
def select_account(request):
    cuentas = Cuenta.objects.filter(usuarios__usuario=request.user, usuarios__activo=True).distinct()
    if request.method == "POST":
        request.session["cuenta_id"] = request.POST.get("cuenta_id")
        return redirect("accounts:admin_dashboard")
    return render(request, "accounts/select_account.html", {"cuentas": cuentas})

@login_required
@require_role("admin", "staff")
def admin_dashboard(request):
    cuenta = get_current_cuenta(request)
    return render(request, "accounts/admin_dashboard.html", {"cuenta": cuenta})
