# accounts/context_processors.py
from .models import Cuenta, UsuarioRol

def cuenta_activa(request):
    """
    Entrega la cuenta activa en el contexto de templates.

    - Primero intenta usar request.session['cuenta_activa_id'].
    - Si no existe, toma la primera cuenta asociada al usuario (por UsuarioRol).
    """
    cuenta = None

    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        # 1) Intentar desde la sesión
        cuenta_id = request.session.get("cuenta_activa_id")
        if cuenta_id:
            try:
                cuenta = Cuenta.objects.get(id=cuenta_id)
            except Cuenta.DoesNotExist:
                cuenta = None

        # 2) Fallback: si no hay en sesión, mirar UsuarioRol
        if cuenta is None:
            rol = (
                UsuarioRol.objects
                .filter(usuario=user, activo=True)
                .select_related("cuenta")
                .first()
            )
            if rol:
                cuenta = rol.cuenta
                # Opcional: podrías guardar esto en sesión si quieres
                # request.session["cuenta_activa_id"] = str(cuenta.id)

    return {"cuenta_activa": cuenta}