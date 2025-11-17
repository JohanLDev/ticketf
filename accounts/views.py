from django.contrib.auth import login
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.views import View
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.http import JsonResponse
from .forms import SignupForm, ProfileForm
from .models import Profile
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from orders.models import Ticket
from django.urls import reverse
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from .models import Cuenta, UsuarioRol
from django.core.exceptions import PermissionDenied


User = get_user_model()


class SimpleLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    # El AuthenticationForm usa el campo 'username', pero internamente respeta USERNAME_FIELD
    # Mapeamos el input 'email' al name 'username' en el template.
    # Por eso no seteamos authentication_form aquí.

class LogoutView(DjangoLogoutView):
    pass

class RegisterForm(forms.ModelForm):
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ["email"]
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class RegisterView(View):
    def get(self, request):
        return render(request, "accounts/register.html", {"form": RegisterForm()})
    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("public:home")
        return render(request, "accounts/register.html", {"form": form})



def register(request):
    """
    Formulario CREAR CUENTA para usuarios normales.
    """
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()

            # Crear usuario base
            user = User.objects.create_user(
                email=email,
                password=form.cleaned_data["password"],
                first_name=form.cleaned_data["nombres"],
                last_name=form.cleaned_data["apellido1"],
            )

            # Crear perfil con TODOS los datos
            profile = Profile.objects.create(
                user=user,
                nombres=form.cleaned_data["nombres"],
                apellido1=form.cleaned_data["apellido1"],
                apellido2=form.cleaned_data.get("apellido2") or "",
                tipo_doc=form.cleaned_data.get("tipo_doc") or "",
                numero_documento=form.cleaned_data.get("numero_documento") or "",
                telefono_movil=form.cleaned_data["telefono_movil"],
                pais=form.cleaned_data["pais"],
                region=form.cleaned_data.get("region") or "",
                ciudad=form.cleaned_data["ciudad"],
                comuna=form.cleaned_data.get("comuna") or "",
                empresa=form.cleaned_data.get("empresa") or "",
                cargo=form.cleaned_data.get("cargo") or "",
                rubro=form.cleaned_data.get("rubro") or "",
                acepta_terminos=form.cleaned_data["acepta_terminos"],
                recibe_novedades=form.cleaned_data.get("recibe_novedades", False),
            )

            # (Aquí sigue igual tu envío de correo de bienvenida, etc.)
            try:
                ctx = {"user": user, "profile": profile}
                subject = "Creaste tu cuenta en [NOMBRE-SITIO]"
                message = render_to_string("accounts/email_welcome.txt", ctx)
                send_mail(
                    subject,
                    message,
                    getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    [email],
                    fail_silently=True,
                )
            except Exception:
                pass

            login(request, user)
            return redirect("accounts:profile")
    else:
        form = SignupForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile_view(request):
    # Aseguramos que exista el profile
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "nombres": request.user.first_name or "",
            "apellido1": request.user.last_name or "",
        },
    )

    # Tickets comprados por este usuario (ajusta "orden" si tu FK se llama distinto)
    tickets = Ticket.objects.filter(orden__comprador_email=request.user.email)

    # Tab activo: 'tickets' o 'datos'
    active_tab = request.GET.get("tab", "datos")

    if request.method == "POST":
        # El POST viene desde el tab "Mis datos"
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save()

            new_password = form.cleaned_data.get("new_password1")
            if new_password:
                request.user.set_password(new_password)
                request.user.save()
                update_session_auth_hash(request, request.user)
                messages.success(
                    request,
                    "Tu contraseña se ha actualizado correctamente.",
                )
            else:
                messages.success(
                    request,
                    "Tu perfil se ha actualizado correctamente.",
                )

            # Volvemos al tab de datos
            return redirect(f"{reverse('accounts:profile')}?tab=datos")
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
            active_tab = "datos"
    else:
        form = ProfileForm(instance=profile)

    context = {
        "form": form,
        "user_email": request.user.email,
        "tickets": tickets,
        "active_tab": active_tab,
    }
    return render(request, "accounts/profile.html", context)




@login_required
def profile_api(request):
    """
    API JSON para que el checkout se autorellene.
    """
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={
            "nombres": request.user.first_name or "",
            "apellido1": request.user.last_name or "",
        },
    )

    data = {
        "email": request.user.email,
        "nombres": profile.nombres,
        "apellido1": profile.apellido1,
        "apellido2": profile.apellido2,
        "telefono_movil": profile.telefono_movil,
        "pais": profile.pais,
        "region": profile.region,
        "ciudad": profile.ciudad,
    }
    return JsonResponse(data)


@login_required
def profile_tabs(request):
    return render(request, "accounts/profile_tabs.html")


@login_required
def user_tickets(request):
    tickets = Ticket.objects.filter(order__comprador_email=request.user.email)
    return render(request, "accounts/user_tickets.html", {"tickets": tickets})



@login_required
def user_ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    # Seguridad: ticket debe pertenecer al usuario
    if ticket.orden.comprador_email != request.user.email:
        raise Http404("No tienes acceso a este ticket.")

    return render(request, "accounts/user_ticket_detail.html", {"ticket": ticket})



def _get_cuenta_activa(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None

    # 1) Intentar desde la sesión
    cuenta_id = request.session.get("cuenta_activa_id")
    if cuenta_id:
        try:
            return Cuenta.objects.get(id=cuenta_id)
        except Cuenta.DoesNotExist:
            pass  # seguimos al fallback

    # 2) Fallback: primer rol activo del usuario
    rol = (
        UsuarioRol.objects
        .filter(usuario=user, activo=True)
        .select_related("cuenta")
        .first()
    )
    if rol:
        cuenta = rol.cuenta
        # opcional: guardamos en sesión para siguientes requests
        request.session["cuenta_activa_id"] = str(cuenta.id)
        return cuenta

    return None

def _es_admin_de_cuenta(request, cuenta):
    if not request.user.is_authenticated:
        return False
    return UsuarioRol.objects.filter(
        usuario=request.user,
        cuenta=cuenta,
        rol="admin",
        activo=True,
    ).exists()

@login_required
def account_plan(request):
    cuenta = _get_cuenta_activa(request)
    if not cuenta:
        messages.error(request, "No hay una cuenta activa seleccionada.")
        return redirect("accounts:select_account")

    if not _es_admin_de_cuenta(request, cuenta) and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para gestionar el plan de esta cuenta.")
        return redirect("accounts:admin_dashboard")

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "upgrade" and cuenta.plan == "basico":
            return redirect("accounts:account_plan_checkout")

        if action == "downgrade" and cuenta.plan == "premium":
            cuenta.plan = "basico"
            cuenta.save()
            messages.success(request, "Has vuelto al plan Básico.")
            return redirect("accounts:admin_dashboard")

    context = {
        "cuenta": cuenta,
        "hide_plan_cta": True,   # 👈 ocultar botón del footer aquí
    }
    return render(request, "accounts/account_plan.html", context)



@login_required
def account_plan_checkout(request):
    cuenta = _get_cuenta_activa(request)
    if not cuenta:
        messages.error(request, "No hay una cuenta activa seleccionada.")
        return redirect("accounts:select_account")

    if not _es_admin_de_cuenta(request, cuenta) and not request.user.is_superuser:
        messages.error(request, "No tienes permisos para gestionar el plan de esta cuenta.")
        return redirect("accounts:admin_dashboard")

    if cuenta.plan == "premium":
        return redirect("accounts:account_plan")

    if request.method == "POST":
        cuenta.plan = "premium"
        cuenta.save()
        messages.success(request, "¡Tu cuenta ahora es Premium!")
        return redirect("accounts:admin_dashboard")

    context = {
        "cuenta": cuenta,
        "hide_plan_cta": True,  
    }
    return render(request, "accounts/account_plan_checkout.html", context)


@login_required
def premium_heatmap(request):
    cuenta = _get_cuenta_activa(request)
    if not cuenta or cuenta.plan != "premium":
        raise PermissionDenied("Esta sección es solo para cuentas Premium.")
    return render(request, "accounts/premium_heatmap.html", {"cuenta": cuenta})

@login_required
def premium_reports(request):
    cuenta = _get_cuenta_activa(request)
    if not cuenta or cuenta.plan != "premium":
        raise PermissionDenied("Esta sección es solo para cuentas Premium.")
    return render(request, "accounts/premium_reports.html", {"cuenta": cuenta})
