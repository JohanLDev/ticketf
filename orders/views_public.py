from django.shortcuts import render, get_object_or_404
from events.models import Evento
from tickets.models import TipoTicket

def _has_field(model, name: str) -> bool:
    return any(f.name == name for f in model._meta.get_fields())

def home_public(request):
    qs = Evento.objects.all()

    # Si tienes un campo "estado", evitamos mostrar borradores/ocultos si existen esos valores.
    # (No rompe si no existen.)
    if _has_field(Evento, "estado"):
        qs = qs.exclude(estado__in=["borrador", "draft", "oculto", "hidden"])

    # Ordenar por fecha de inicio si existe; si no, por id descendente.
    order_field = "-fecha_inicio" if _has_field(Evento, "fecha_inicio") else "-id"
    eventos = qs.order_by(order_field)[:20]

    return render(request, "orders/public_home.html", {"eventos": eventos})


def event_public_detail(request, slug):
    # Cargamos el evento por slug (no filtro estado porque no vi el campo en tu modelo)
    event = get_object_or_404(Evento, slug=slug)
    context = {
        "event": event,
    }
    return render(request, "orders/public_event_detail.html", context)

def checkout_step1(request, slug):
    event = get_object_or_404(Evento, slug=slug)
    # Mostrar sólo tipos activos; si luego agregás visibilidad por fechas/stock, lo ajustamos aquí
    tipos = TipoTicket.objects.filter(evento=event, activo=True).order_by("nombre")
    context = {
        "event": event,
        "tipos": tipos,
    }
    return render(request, "orders/public_checkout_step1.html", context)

def checkout_success(request, order_id: int):
    from orders.models import Orden, Ticket
    orden = get_object_or_404(Orden, id=order_id)
    tickets = Ticket.objects.filter(orden=orden).select_related("tipo")
    return render(request, "orders/public_checkout_success.html", {
        "orden": orden,
        "tickets": tickets,
    })

def checkout_step3_form(request, slug):
    from events.models import Evento
    event = get_object_or_404(Evento, slug=slug)
    # El formulario se llenará en el front y validará en JS.
    return render(request, "orders/public_checkout_step3.html", {"event": event})

def public_checkout_pay(request, slug):
    evento = get_object_or_404(Evento, slug=slug)
    return render(request, 'orders/public_checkout_pay.html', {'event': evento})