from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Cuenta
from .utils import get_current_cuenta, require_role

@login_required
def select_account(request):
    if request.user.is_superuser:
        # Superadmin ve todas: activas e inactivas
        cuentas = Cuenta.objects.all().order_by("nombre")
    else:
        # Usuario normal solo ve cuentas activas donde es admin
        cuentas = (
            Cuenta.objects
            .filter(
                usuarios__usuario=request.user,
                usuarios__activo=True,
                estado="activo",          # ⬅️ filtro agregado
            )
            .distinct()
            .order_by("nombre")
        )

    if request.method == "POST":
        request.session["cuenta_id"] = request.POST.get("cuenta_id")
        return redirect("accounts:admin_dashboard")

    return render(request, "accounts/select_account.html", {"cuentas": cuentas})


@login_required
@require_role("admin", "staff")
def admin_dashboard(request):
    cuenta = get_current_cuenta(request)
    return render(request, "accounts/admin_dashboard.html", {"cuenta": cuenta})
