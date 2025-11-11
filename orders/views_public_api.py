# orders/views_public_api.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404
from events.models import Evento
from tickets.models import TipoTicket
from .services.checkout import crear_orden_y_tickets
from django.views.decorators.csrf import csrf_exempt

from tickets.models import DiscountCode, TipoTicket

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def checkout_crear_orden(request):
    """
    Crea una Orden y Tickets para un evento público (simulado, sin pasarela).
    Payload esperado:
    {
      "evento_slug": "mi-evento",
      "comprador_email": "mail@dominio.com",
      "items": [{"tipo_ticket_id": 1, "cantidad": 2}, ...]
    }
    """
    data = request.data or {}
    slug = data.get("evento_slug")
    comprador_email = data.get("comprador_email")
    items_payload = data.get("items", [])
    promo_code = data.get("promo_code")

    if not slug or not comprador_email or not isinstance(items_payload, list) or not items_payload:
        return Response({"detail": "Payload inválido."}, status=status.HTTP_400_BAD_REQUEST)

    evento = get_object_or_404(Evento, slug=slug)

    # Resolver tipos y cantidades
    tipo_ids = [it.get("tipo_ticket_id") for it in items_payload if it.get("tipo_ticket_id") is not None]
    tipos = {tt.id: tt for tt in TipoTicket.objects.filter(id__in=tipo_ids, evento=evento)}

    items = []
    for it in items_payload:
        tt_id = it.get("tipo_ticket_id")
        qty = int(it.get("cantidad") or 0)
        tt = tipos.get(tt_id)

        if not tt:
            return Response({"detail": f"TipoTicket {tt_id} no pertenece al evento."},
                            status=status.HTTP_400_BAD_REQUEST)
        if qty <= 0:
            return Response({"detail": f"Cantidad inválida para tipo {tt_id}."},
                            status=status.HTTP_400_BAD_REQUEST)
        if getattr(tt, "is_parking", False) and qty > 1:
            return Response({"detail": "Estacionamiento: máximo 1 por orden."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not getattr(tt, "is_parking", False) and qty > 10:
            return Response({"detail": f"Máximo 10 por tipo {tt_id}."},
                            status=status.HTTP_400_BAD_REQUEST)

        items.append({"tipo_ticket": tt, "cantidad": qty})


    try:
        orden, tickets = crear_orden_y_tickets(
            evento=evento,
            comprador_email=comprador_email,
            items=items,
            created_by=None,
            promo_code=promo_code,
        )
    except ValueError as e:
        return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Armar respuesta mínima (sin totales porque tu modelo no los tiene)
    return Response({
        "order_id": orden.id,
        "evento": evento.slug,
        "comprador_email": orden.comprador_email,
        "tickets": [{"id": t.id, "code": str(t.code), "tipo_ticket_id": t.tipo_id} for t in tickets],
        "created_at": orden.created_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def validar_promocode(request):
    """
    Payload:
    {
      "evento_slug": "aquasur-2026",
      "code": "DESCUENTO10",
      "items": [{"tipo_ticket_id": 1, "cantidad": 2}, ...]
    }
    Respuesta (200):
    { "ok": true/false, "message": str, "discount_amount": int }
    """
    data = request.data or {}
    slug = data.get("evento_slug")
    code = (data.get("code") or "").strip()
    items = data.get("items") or []

    if not slug or not code or not isinstance(items, list):
        return Response({"ok": False, "message": "Payload inválido."}, status=400)

    evento = get_object_or_404(Evento, slug=slug)
    try:
        d = DiscountCode.objects.select_related("evento", "tipo_ticket", "evento__cuenta") \
                                .get(codigo__iexact=code, evento=evento)
    except DiscountCode.DoesNotExist:
        return Response({"ok": False, "message": "El código ingresado no es válido."}, status=200)

    if not d.disponible():
        return Response({"ok": False, "message": "Este código ya fue utilizado o fuera de vigencia."}, status=200)

    # Si exige tipo_ticket, debe estar en el carrito
    if d.tipo_ticket_id:
        present = any(int(it.get("tipo_ticket_id") or 0) == d.tipo_ticket_id and int(it.get("cantidad") or 0) > 0 for it in items)
        if not present:
            return Response({"ok": False, "message": "El código aplica a un tipo de ticket específico no presente en tu selección."}, status=200)

    # Descuento: monto fijo sobre TOTAL (no per-item)
    discount_amount = int(d.monto_descuento or 0)
    if discount_amount <= 0:
        return Response({"ok": False, "message": "El código no tiene un monto válido."}, status=200)

    return Response({"ok": True, "message": "Código aplicado.", "discount_amount": discount_amount}, status=200)
