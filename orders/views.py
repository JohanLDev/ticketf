# Python estándar
from io import BytesIO
import qrcode

# Django core
from django import forms
from django.forms import IntegerField
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.utils.timezone import now
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

# Apps del proyecto
from accounts.utils import get_current_cuenta, require_role
from events.models import Evento
from tickets.models import TipoTicket
from .models import Orden, Ticket, ValidationLog
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from xhtml2pdf import pisa
import io, base64, qrcode
from django.db import transaction



# ---------- FORMULARIO ----------
class OrderForm(forms.Form):
    evento = forms.ModelChoiceField(queryset=Evento.objects.none(), label="Evento")
    tipo = forms.ModelChoiceField(queryset=TipoTicket.objects.none(), label="Tipo de ticket")
    cantidad = IntegerField(min_value=1, max_value=50, initial=1, label="Cantidad")
    comprador_email = forms.EmailField(label="Email comprador")

    def __init__(self, cuenta, *args, **kwargs):
        """
        - Carga eventos de la cuenta.
        - Cuando eliges un evento, recarga el formulario (GET) para poblar 'tipo'.
        """
        super().__init__(*args, **kwargs)

        # 1) Eventos de la cuenta
        self.fields["evento"].queryset = Evento.objects.filter(cuenta=cuenta)

        # 2) Al cambiar evento, recargar como GET para poblar 'tipo'
        self.fields["evento"].widget.attrs.update({
            "onchange": "this.form.method='get'; this.form.submit();"
        })

        # 3) Detectar evento seleccionado (desde GET o desde el POST)
        ev_id = (self.data.get("evento")
                 or self.initial.get("evento")
                 or kwargs.get("initial", {}).get("evento"))

        evento_seleccionado = (
            Evento.objects.filter(pk=ev_id, cuenta=cuenta).first()
            if ev_id else None
        )

        # 4) Poblar tipos según evento (o vacío si aún no hay evento)
        self.fields["tipo"].queryset = (
            TipoTicket.objects.filter(evento=evento_seleccionado)
            if evento_seleccionado else TipoTicket.objects.none()
        )


# ---------- VISTAS ----------
@require_role("admin", "staff")
def order_list(request):
    cuenta = get_current_cuenta(request)
    qs = Orden.objects.filter(cuenta=cuenta).select_related("evento")
    return render(request, "orders/list.html", {"ordenes": qs})



@require_role("superadmin", "admin", "staff")
def order_create(request):
    cuenta = get_current_cuenta(request)
    eventos = Evento.objects.filter(cuenta=cuenta)

    if request.method == "POST":
        evento = get_object_or_404(Evento, id=request.POST["evento"], cuenta=cuenta)
        email = request.POST.get("email") or ""
        tipos = TipoTicket.objects.filter(evento=evento, activo=True)

        # Creamos la orden primero
        with transaction.atomic():
            orden = Orden.objects.create(cuenta=cuenta, evento=evento, comprador_email=email)

            total_tickets = 0
            for tipo in tipos:
                cantidad = int(request.POST.get(f"cantidad_{tipo.id}", 0))
                for _ in range(cantidad):
                    Ticket.objects.create(
                        orden=orden,
                        evento=evento,
                        tipo=tipo,
                        asistente_email=email,
                    )
                    total_tickets += 1

        msg = f"{total_tickets} tickets generados para la orden #{orden.id}"
        return redirect("orders:detail", pk=orden.id)

    return render(request, "orders/create.html", {"eventos": eventos})


@require_role("superadmin", "admin", "staff")
def order_detail(request, pk):
    cuenta = get_current_cuenta(request)
    orden = get_object_or_404(Orden, pk=pk, cuenta=cuenta)
    tickets = orden.tickets.select_related("tipo", "evento").all()

    total = tickets.count()
    usados = tickets.filter(estado="quemado").count()
    disponibles = tickets.filter(estado="disponible").count()

    resumen = {
        "total": total,
        "usados": usados,
        "disponibles": disponibles,
    }

    return render(request, "orders/detail.html", {
        "orden": orden,
        "tickets": tickets,
        "resumen": resumen,
    })


# ---------- QR ----------
def ticket_qr(request, code):
    ticket = Ticket.objects.filter(code=code).first()
    if not ticket:
        return HttpResponse(status=404)
    img = qrcode.make(code)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return HttpResponse(buf.getvalue(), content_type="image/png")


# ---------- VALIDACIÓN ----------
@require_http_methods(["POST"])
@login_required
def validate_ticket(request, code):
    cuenta = get_current_cuenta(request)
    t = Ticket.objects.select_related("evento", "tipo").filter(code=code).first()

    if not t:
        ValidationLog.objects.create(
            cuenta=cuenta, result='NOT_FOUND', note='TICKET_NOT_FOUND',
            ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT',''),
            usuario=request.user
        )
        return JsonResponse({"ok": False, "error": "TICKET_NOT_FOUND"}, status=404)

    # (opcional) asegurar misma cuenta
    if t.evento.cuenta_id != cuenta.id:
        ValidationLog.objects.create(
            cuenta=cuenta, ticket=t, evento=t.evento, result='DENIED', note='ACCOUNT_MISMATCH',
            ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT',''),
            usuario=request.user
        )
        return JsonResponse({"ok": False, "error": "ACCOUNT_MISMATCH"}, status=403)

    if t.estado == "quemado":
        ValidationLog.objects.create(
            cuenta=cuenta, ticket=t, evento=t.evento, result='ALREADY_USED', note='REPEAT',
            ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT',''),
            usuario=request.user
        )
        return JsonResponse(
            {"ok": False, "error": "ALREADY_USED", "used_at": t.used_at, "tipo": t.tipo.nombre, "evento": t.evento.nombre},
            status=409
        )

    # OK: marcar usado
    t.estado = "quemado"
    t.used_at = now()
    t.save(update_fields=["estado", "used_at"])

    ValidationLog.objects.create(
        cuenta=cuenta, ticket=t, evento=t.evento, result='OK',
        ip=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT',''),
        usuario=request.user
    )

    return JsonResponse({"ok": True, "code": str(t.code), "evento": t.evento.nombre, "tipo": t.tipo.nombre})


@require_role("admin","staff")
def validator_page(request):
    """
    Página de validación con autofocus. El input recibe el código del QR (uuid).
    Envía POST a /orders/validate/<code>/ y muestra el resultado sin recargar.
    """
    return render(request, "orders/validator.html")


def _qr_data_url(data: str) -> str:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

def ticket_pdf_by_code(request, code):
    ticket = get_object_or_404(Ticket, code=code)

    context = {
        "ticket": ticket,
        "qr_data_url": _qr_data_url(str(ticket.code)),
    }
    html = render_to_string("orders/ticket_pdf.html", context)

    result = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=result)
    pdf = result.getvalue()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="ticket_{ticket.id}.pdf"'
    return resp

@login_required
def ticket_pdf_by_user(request, code):
    ticket = get_object_or_404(Ticket, code=code)

    # Seguridad: el ticket debe pertenecer al usuario logeado
    if ticket.asistente_email != request.user.email and \
       ticket.orden.comprador_email != request.user.email:
        raise Http404("No tienes acceso a este ticket.")

    # Reutilizamos tu generador de PDF REAL
    return ticket_pdf_by_code(request, code)