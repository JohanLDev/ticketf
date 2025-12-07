# orders/views_reports.py
import io
from datetime import datetime
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.db.models import Count
from django.db.models.functions import TruncDate
from xhtml2pdf import pisa

from accounts.utils import get_current_cuenta, require_role
from events.models import Evento
from .models import Ticket

from django.db.models import Sum, F
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required


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


@login_required
def event_financial_report(request, event_id):
    """
    Reporte financiero por evento:
    - Total $ por tipo de ticket
    - Total $ estacionamiento vs otros
    - Totales brutos (sin considerar descuentos explícitos)
    - Cantidades de tickets y porcentajes
    """
    evento = get_object_or_404(Evento, id=event_id)

    # Tickets del evento, excluyendo anulados
    tickets = (
        Ticket.objects
        .select_related("tipo")
        .filter(evento=evento)
        .exclude(estado="anulado")
    )

    # Totales de monto
    total_bruto = tickets.aggregate(
        total=Sum(F("tipo__precio"))
    )["total"] or 0

    total_parking = tickets.filter(tipo__is_parking=True).aggregate(
        total=Sum(F("tipo__precio"))
    )["total"] or 0

    total_no_parking = total_bruto - total_parking

    # Cantidades de tickets
    total_tickets = tickets.count()
    parking_tickets = tickets.filter(tipo__is_parking=True).count()
    no_parking_tickets = total_tickets - parking_tickets

    # Porcentajes (por monto y por cantidad)
    if total_bruto > 0:
        parking_pct_amount = round(total_parking * 100 / total_bruto, 1)
    else:
        parking_pct_amount = 0.0

    if total_tickets > 0:
        parking_pct_count = round(parking_tickets * 100 / total_tickets, 1)
    else:
        parking_pct_count = 0.0

    # Totales por tipo de ticket (incluye precio unitario)
    totales_por_tipo = (
        tickets.values("tipo__nombre", "tipo__is_parking")
        .annotate(
            cantidad=Count("id"),
            monto=Sum(F("tipo__precio")),
            precio=F("tipo__precio"),
        )
        .order_by("tipo__nombre")
    )

    # Por ahora no tenemos montos de descuento guardados en Orden
    descuentos_totales = 0
    total_neto = total_bruto - descuentos_totales

    contexto = {
        "evento": evento,
        "total_bruto": total_bruto,
        "total_parking": total_parking,
        "total_no_parking": total_no_parking,
        "descuentos_totales": descuentos_totales,
        "total_neto": total_neto,
        "totales_por_tipo": totales_por_tipo,

        # nuevas métricas
        "total_tickets": total_tickets,
        "parking_tickets": parking_tickets,
        "no_parking_tickets": no_parking_tickets,
        "parking_pct_amount": parking_pct_amount,
        "parking_pct_count": parking_pct_count,
    }

    return render(request, "orders/event_financial_report.html", contexto)