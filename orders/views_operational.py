from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from accounts.utils import get_current_cuenta, require_role
from .models import Ticket, TicketActionLog
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from events.models import Evento
from .models import Orden
from django.core.paginator import Paginator
from django.db.models import Q


@require_POST
@require_role("superadmin", "admin")
def ticket_cancel(request, ticket_id):
    cuenta = get_current_cuenta(request)
    t = get_object_or_404(Ticket, pk=ticket_id, evento__cuenta=cuenta)
    if t.estado == "anulado":
        messages.info(request, f"El ticket #{t.id} ya estaba anulado.")
        return redirect("orders:detail", pk=t.orden_id)
    t.estado = "anulado"
    t.save(update_fields=["estado"])
    TicketActionLog.objects.create(
        ticket=t, action="anular", performed_by=request.user, reason=request.POST.get("reason", "")
    )
    messages.success(request, f"Ticket #{t.id} anulado.")
    return redirect("orders:detail", pk=t.orden_id)

@require_POST
@require_role("superadmin", "admin")
@transaction.atomic
def ticket_reissue(request, ticket_id):
    cuenta = get_current_cuenta(request)
    old = get_object_or_404(Ticket, pk=ticket_id, evento__cuenta=cuenta)

    # 1) Anula el ticket original (si no lo está)
    if old.estado != "anulado":
        old.estado = "anulado"
        old.save(update_fields=["estado"])
        TicketActionLog.objects.create(ticket=old, action="anular", performed_by=request.user, reason="Reemisión")

    # 2) Crea el reemplazo (mismo orden, evento y tipo)
    new_t = Ticket.objects.create(
        orden=old.orden,
        evento=old.evento,
        tipo=old.tipo,
        asistente_email=old.asistente_email,
    )
    old.replaced_by = new_t
    old.save(update_fields=["replaced_by"])

    TicketActionLog.objects.create(
        ticket=new_t, action="reemitir", performed_by=request.user, reason=f"Reemplaza al #{old.id}"
    )

    messages.success(request, f"Creado ticket de reemplazo #{new_t.id} para el #{old.id}.")
    return redirect("orders:detail", pk=old.orden_id)


@require_role("superadmin", "admin", "staff")
def orders_by_event(request, event_id):
    cuenta = get_current_cuenta(request)
    evento = get_object_or_404(Evento, id=event_id, cuenta=cuenta)

    qs = (
        Orden.objects
        .filter(cuenta=cuenta, evento=evento)
        .select_related("evento")
        .order_by("-created_at")
    )

    # -------- Filtros --------
    q = (request.GET.get("q") or "").strip()
    desde = request.GET.get("desde") or ""
    hasta = request.GET.get("hasta") or ""

    if q:
        qs = qs.filter(
            Q(id__icontains=q) |
            Q(comprador_email__icontains=q)
        )

    if desde:
        qs = qs.filter(created_at__date__gte=desde)
    if hasta:
        qs = qs.filter(created_at__date__lte=hasta)

    # -------- Paginación --------
    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    contexto = {
        "evento": evento,
        "ordenes": page_obj.object_list,
        "page_obj": page_obj,
        "q": q,
        "desde": desde,
        "hasta": hasta,
    }
    return render(request, "orders/list.html", contexto)
