from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST
from django.core.mail import EmailMessage
from xhtml2pdf import pisa
import io, base64, qrcode
from accounts.utils import get_current_cuenta, require_role
from .models import Ticket, Orden


def _qr_data_url(data: str) -> str:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

def _render_ticket_pdf_bytes(ticket) -> bytes:
    html = render_to_string("orders/ticket_pdf.html", {
        "ticket": ticket,
        "qr_data_url": _qr_data_url(str(ticket.code)),
    })
    out = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=out)
    return out.getvalue()

@require_POST
@require_role("superadmin", "admin", "staff")   # 👈 protege la vista
def ticket_email_by_code(request, code):
    cuenta = get_current_cuenta(request)
    ticket = get_object_or_404(Ticket, code=code)
    if not cuenta or ticket.orden.cuenta_id != cuenta.id:
        raise Http404()

    # email alternativo opcional
    to = (request.POST.get("email") or ticket.orden.comprador_email or "").strip()
    if not to:
        return JsonResponse({"ok": False, "error": "Sin email destino"}, status=400)

    # plantilla y asunto según estacionamiento
    if getattr(ticket.tipo, "is_parking", False):
        subject = f"[{ticket.evento.nombre}] Estacionamiento · Ticket #{ticket.id}"
        body = render_to_string("orders/email_parking.txt", {"ticket": ticket})
    else:
        subject = f"[{ticket.evento.nombre}] Tu ticket #{ticket.id}"
        body = render_to_string("orders/email_ticket.txt", {"ticket": ticket})

    pdf = _render_ticket_pdf_bytes(ticket)

    email = EmailMessage(subject, body, to=[to])
    email.attach(filename=f"ticket_{ticket.id}.pdf", content=pdf, mimetype="application/pdf")
    email.send(fail_silently=False)

    return JsonResponse({"ok": True, "sent_to": to, "parking": getattr(ticket.tipo, "is_parking", False)})

@require_POST
@require_role("superadmin","admin","staff")
def order_email_all(request, order_id):
    cuenta = get_current_cuenta(request)
    orden = get_object_or_404(Orden, pk=order_id, cuenta=cuenta)
    to = (request.POST.get("email") or orden.comprador_email or "").strip()
    if not to:
        return JsonResponse({"ok": False, "error": "Sin email destino"}, status=400)

    enviados = []
    for t in orden.tickets.select_related("tipo"):
        pdf = _render_ticket_pdf_bytes(t)
        if getattr(t.tipo, "is_parking", False):
            subject = f"[{t.evento.nombre}] Estacionamiento · Ticket #{t.id}"
            body = render_to_string("orders/email_parking.txt", {"ticket": t})
        else:
            subject = f"[{t.evento.nombre}] Tu ticket #{t.id}"
            body = render_to_string("orders/email_ticket.txt", {"ticket": t})

        email = EmailMessage(subject, body, to=[to])
        email.attach(filename=f"ticket_{t.id}.pdf", content=pdf, mimetype="application/pdf")
        email.send(fail_silently=False)
        enviados.append(str(t.id))

    return JsonResponse({"ok": True, "sent_to": to, "tickets": enviados})