# orders/views_reports.py
import io
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.db.models import Count
from django.db.models.functions import TruncDate
from xhtml2pdf import pisa

from accounts.utils import get_current_cuenta, require_role
from events.models import Evento
from .models import Ticket

@require_role("superadmin", "admin", "staff")
def event_report_pdf(request, event_id):
    cuenta = get_current_cuenta(request)
    evento = get_object_or_404(Evento, pk=event_id, cuenta=cuenta)

    tickets = Ticket.objects.filter(evento=evento)

    emitidos = tickets.count()
    validados = tickets.filter(estado="quemado").count()
    anulados = tickets.filter(estado="anulado").count() if "anulado" in [c[0] for c in Ticket._meta.get_field("estado").choices] else 0
    asistencia = round((validados / emitidos * 100), 2) if emitidos else 0

    # Distribución por tipo (emitidos)
    tipos_data = list(
        tickets.values("tipo__nombre")
        .annotate(total=Count("id"))
        .order_by("tipo__nombre")
    )

    # Validados por tipo
    validados_por_tipo = list(
        tickets.filter(estado="quemado")
        .values("tipo__nombre")
        .annotate(total=Count("id"))
        .order_by("tipo__nombre")
    )

    # Validados por día (para tabla resumida)
    validados_por_dia = list(
        tickets.filter(estado="quemado", used_at__isnull=False)
        .annotate(dia=TruncDate("used_at"))
        .values("dia")
        .annotate(total=Count("id"))
        .order_by("dia")
    )

    contexto = {
        "evento": evento,
        "ahora": datetime.now(),
        "resumen": {
            "emitidos": emitidos,
            "validados": validados,
            "anulados": anulados,
            "asistencia": asistencia,
        },
        "tipos_data": tipos_data,
        "validados_por_tipo": validados_por_tipo,
        "validados_por_dia": validados_por_dia,
    }

    html = render_to_string("orders/event_report.html", contexto)
    out = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=out)
    pdf = out.getvalue()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f'inline; filename="reporte_evento_{evento.id}.pdf"'
    return resp
