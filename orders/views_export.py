import csv
from django.http import StreamingHttpResponse
from django.utils.timezone import localtime
from django.shortcuts import get_object_or_404
from accounts.utils import get_current_cuenta, require_role
from events.models import Evento
from .models import Ticket

@require_role("superadmin", "admin", "staff")
def export_event_tickets_csv(request, event_id):
    cuenta = get_current_cuenta(request)
    evento = get_object_or_404(Evento, pk=event_id, cuenta=cuenta)

    tickets = (
        Ticket.objects
        .filter(evento=evento)
        .select_related("orden", "tipo", "evento")
        .order_by("id")
    )

    def generate():
        header = [
            "ticket_id", "tipo_ticket", "comprador_email",
            "asistente_email", "estado", "used_at", "evento", "orden_id"
        ]
        yield ",".join(header) + "\n"
        for t in tickets.iterator():
            yield ",".join([
                str(t.id),
                t.tipo.nombre,
                t.orden.comprador_email or "",
                t.asistente_email or "",
                t.estado,
                localtime(t.used_at).isoformat() if t.used_at else "",
                t.evento.nombre,
                str(t.orden_id),
            ]) + "\n"

    resp = StreamingHttpResponse(generate(), content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="event_{evento.id}_tickets.csv"'
    return resp
