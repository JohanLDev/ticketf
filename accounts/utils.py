from django.shortcuts import redirect
from functools import wraps
from .models import Cuenta, UsuarioRol

def get_current_cuenta(request):
    cid = request.session.get("cuenta_id")
    if not cid:
        return None
    return Cuenta.objects.filter(id=cid).first()

def require_role(*roles):
    def deco(viewfunc):
        @wraps(viewfunc)
        def _wrapped(request, *args, **kwargs):
            cuenta = get_current_cuenta(request)
            if not cuenta:
                return redirect("accounts:select_account")
            ok = UsuarioRol.objects.filter(
                usuario=request.user, cuenta=cuenta, rol__in=roles, activo=True
            ).exists()
            if not ok:
                return redirect("public:home")
            return viewfunc(request, *args, **kwargs)
        return _wrapped
    return deco
