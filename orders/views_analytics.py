from django.shortcuts import get_object_or_404, render
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from accounts.utils import get_current_cuenta, require_role
from events.models import Evento
from .models import Ticket
from django.utils.dateparse import parse_date


# --- Vista principal del dashboard ---
@require_role("superadmin", "admin", "staff")
def event_summary(request, event_id):
    cuenta = get_current_cuenta(request)
    evento = get_object_or_404(Evento, pk=event_id, cuenta=cuenta)
    tickets = Ticket.objects.filter(evento=evento)

    emitidos = tickets.count()
    validados = tickets.filter(estado="quemado").count()
    anulados = tickets.filter(estado="anulado").count() if "anulado" in [c[0] for c in Ticket._meta.get_field("estado").choices] else 0
    asistencia = round((validados / emitidos * 100), 2) if emitidos else 0

    tipos_data = list(tickets.values("tipo__nombre").annotate(total=Count("id")).order_by("tipo__nombre"))
    validados_por_tipo = list(
        tickets.filter(estado="quemado")
        .values("tipo__nombre")
        .annotate(total=Count("id"))
        .order_by("tipo__nombre")
    )
    validados_por_dia = list(
        tickets.filter(estado="quemado", used_at__isnull=False)
        .annotate(dia=TruncDate("used_at"))
        .values("dia")
        .annotate(total=Count("id"))
        .order_by("dia")
    )

    # Comparativo: emitidos vs validados
    emitidos_vs_validados = []
    for tipo in tipos_data:
        nombre = tipo["tipo__nombre"]
        emitidos_count = tipo["total"]
        validados_count = next((v["total"] for v in validados_por_tipo if v["tipo__nombre"] == nombre), 0)
        emitidos_vs_validados.append({
            "tipo": nombre,
            "emitidos": emitidos_count,
            "validados": validados_count,
        })

    contexto = {
        "evento": evento,
        "resumen": {
            "emitidos": emitidos,
            "validados": validados,
            "anulados": anulados,
            "asistencia": asistencia,
        },
        "tipos_data": tipos_data,
        "validados_por_tipo": validados_por_tipo,
        "validados_por_dia": validados_por_dia,
        "emitidos_vs_validados": emitidos_vs_validados,
    }

    return render(request, "orders/event_dashboard.html", contexto)


# --- Endpoint de datos filtrados para AJAX ---
@require_role("superadmin", "admin", "staff")
def event_summary_data(request, event_id):
    cuenta = get_current_cuenta(request)
    evento = get_object_or_404(Evento, pk=event_id, cuenta=cuenta)
    tickets = Ticket.objects.filter(evento=evento)

    # filtros de fecha
    desde = parse_date(request.GET.get("desde"))
    hasta = parse_date(request.GET.get("hasta"))
    if desde:
        tickets = tickets.filter(created_at__date__gte=desde)
    if hasta:
        tickets = tickets.filter(created_at__date__lte=hasta)

    emitidos = tickets.count()
    validados = tickets.filter(estado="quemado").count()
    anulados = tickets.filter(estado="anulado").count() if "anulado" in [c[0] for c in Ticket._meta.get_field("estado").choices] else 0
    asistencia = round((validados / emitidos * 100), 2) if emitidos else 0

    tipos_data = list(tickets.values("tipo__nombre").annotate(total=Count("id")).order_by("tipo__nombre"))
    validados_por_tipo = list(
        tickets.filter(estado="quemado")
        .values("tipo__nombre")
        .annotate(total=Count("id"))
        .order_by("tipo__nombre")
    )
    validados_por_dia = list(
        tickets.filter(estado="quemado", used_at__isnull=False)
        .annotate(dia=TruncDate("used_at"))
        .values("dia")
        .annotate(total=Count("id"))
        .order_by("dia")
    )

    # Comparativo emitidos vs validados
    emitidos_vs_validados = []
    for tipo in tipos_data:
        nombre = tipo["tipo__nombre"]
        emitidos_count = tipo["total"]
        validados_count = next((v["total"] for v in validados_por_tipo if v["tipo__nombre"] == nombre), 0)
        emitidos_vs_validados.append({
            "tipo": nombre,
            "emitidos": emitidos_count,
            "validados": validados_count,
        })

    data = {
        "resumen": {
            "emitidos": emitidos,
            "validados": validados,
            "anulados": anulados,
            "asistencia": asistencia,
        },
        "tipos": tipos_data,
        "validados_tipo": validados_por_tipo,
        "validados_dia": validados_por_dia,
        "emitidos_vs_validados": emitidos_vs_validados,
    }

    return JsonResponse(data)
