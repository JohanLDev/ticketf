from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from accounts.utils import get_current_cuenta, require_role
from .models import Ticket
from xhtml2pdf import pisa
import io, base64, qrcode
from accounts.utils import get_current_cuenta, require_role

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib import colors

from qrcode.image.pil import PilImage


def _qr_data_url(data: str) -> str:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


@require_role("superadmin","admin","staff")
def ticket_pdf_by_code(request, code):
    cuenta = get_current_cuenta(request)
    ticket = get_object_or_404(Ticket, code=code)
    if ticket.orden.cuenta != cuenta:
      raise Http404()

    context = {"ticket": ticket, "qr_data_url": _qr_data_url(str(ticket.code))}
    html = render_to_string("orders/ticket_pdf.html", context)

    # generar PDF in-memory con xhtml2pdf
    result = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=result)
    pdf = result.getvalue()
    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="ticket_{ticket.id}.pdf"'
    return resp

def order_tickets_pdf(request, order_id: int):
    from orders.models import Orden, Ticket

    orden = get_object_or_404(Orden, id=order_id)
    tickets = list(Ticket.objects.filter(orden=orden).select_related("tipo", "evento"))

    if not tickets:
        raise Http404("No hay tickets para esta orden.")

    # --- PDF en memoria
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    for idx, t in enumerate(tickets, start=1):
        # Cabecera simple
        c.setFont("Helvetica-Bold", 16)
        c.drawString(20*mm, height - 20*mm, f"{t.evento.nombre}")
        c.setFont("Helvetica", 12)
        c.drawString(20*mm, height - 28*mm, f"Orden #{orden.id}  •  Ticket #{t.id}")
        c.drawString(20*mm, height - 36*mm, f"Tipo: {t.tipo.nombre}")
        c.drawString(20*mm, height - 44*mm, f"Código: {t.code}")

        # Generar QR como imagen PIL
        qr_img = qrcode.make(str(t.code))
        qr_size = 40 * mm

        # Convertir a imagen compatible con ReportLab
        qr_img = qr_img.convert("RGB")
        qr_io = BytesIO()
        qr_img.save(qr_io, format="PNG")
        qr_io.seek(0)

        # Dibujar QR en el PDF (ahora funciona)
        c.drawInlineImage(qr_img, width - 20*mm - qr_size, height - 20*mm - qr_size, qr_size, qr_size)


        # Marco tipo “ticket”
        c.setStrokeColor(colors.grey)
        c.rect(15*mm, 15*mm, width - 30*mm, height - 60*mm, stroke=1, fill=0)

        # Pie de página
        c.setFont("Helvetica-Oblique", 9)
        c.drawRightString(width - 15*mm, 12*mm, f"Página {idx} de {len(tickets)}")

        c.showPage()

    c.save()
    buffer.seek(0)

    filename = f"orden_{orden.id}_tickets.pdf"
    return HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )