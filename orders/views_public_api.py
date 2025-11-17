import json
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from events.models import Evento
from .models import Orden
from django.http import JsonResponse, HttpResponseBadRequest
from orders.models import SharedPurchaseCode
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.urls import reverse
from tickets.models import TipoTicket, DiscountCode
from orders.services.checkout import (
    finalizar_pago_y_generar_codigo,
    aplicar_shared_code_en_carrito,
    confirmar_compra_con_shared_code,
)


def _clean_email(v: str) -> str:
    return (v or "").strip().lower()


@csrf_exempt  # puedes quitar el csrf_exempt si prefieres protegerlo con CSRF + header
def checkout_crear_orden(request):
    """
    Crea la orden y los tickets a partir del payload del front.

    Espera JSON:
      {
        "evento_slug": "...",
        "items": [
          {"tipo_ticket_id": 1, "cantidad": 2},
          ...
        ],
        "buyer": {...},
        "comprador_email": "...",   # opcional, se toma desde buyer.email
        "promo_code": "CODIGO"      # opcional
      }

    Responde:
      {
        "order_id": <id>,
        "success_url": "/orders/public/checkout/success/<id>/"
      }
    """
    if request.method != "POST":
        return JsonResponse({"detail": "Método no permitido."}, status=405)

    # Leer JSON
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    evento_slug = data.get("evento_slug")
    items = data.get("items") or []
    buyer = data.get("buyer") or {}
    comprador_email = _clean_email(buyer.get("email") or data.get("comprador_email"))

    promo_code = (data.get("promo_code") or "").strip() or None

    if not evento_slug or not items:
        return JsonResponse(
            {"detail": "Faltan datos (evento o items)."},
            status=400,
        )

    evento = get_object_or_404(Evento, slug=evento_slug)

    # Transacción para consistencia
    with transaction.atomic():
        # Crear orden
        orden = Orden.objects.create(
            cuenta=evento.cuenta,
            evento=evento,
            comprador_email=comprador_email or "",
        )

        # Creamos tickets + construimos carrito para aplicar shared_code
        tipos_map = {}
        carrito = []  # [{ 'tipo': TipoTicket, 'cantidad': int, 'precio_unitario': Decimal }, ...]

        for it in items:
            try:
                tt_id = int(it.get("tipo_ticket_id"))
                cantidad = int(it.get("cantidad"))
            except Exception:
                return JsonResponse({"detail": "Ítems inválidos."}, status=400)

            if cantidad <= 0:
                continue

            if tt_id not in tipos_map:
                tipos_map[tt_id] = get_object_or_404(
                    TipoTicket,
                    pk=tt_id,
                    evento=evento,
                )
            tipo = tipos_map[tt_id]

            # Crear los tickets físicos
            for _ in range(cantidad):
                orden.tickets.create(evento=evento, tipo=tipo)

            carrito.append({
                "tipo": tipo,
                "cantidad": cantidad,
                "precio_unitario": Decimal(tipo.precio),
            })

        # Aplicar/consumir código si viene uno
        if promo_code:
            # 1) Intentamos consumir DiscountCode
            dc = (
                DiscountCode.objects
                .select_for_update()
                .filter(evento=evento, codigo__iexact=promo_code, activo=True)
                .first()
            )

            hoy = timezone.now().date()

            if dc:
                # mismas validaciones que en la vista de validación
                if (
                    (not dc.vigente_desde or hoy >= dc.vigente_desde)
                    and (not dc.vigente_hasta or hoy <= dc.vigente_hasta)
                    and (dc.usos_maximos is None or dc.usos_actuales < dc.usos_maximos)
                ):
                    # si exige tipo_ticket, verificamos que esté en el carrito
                    if not dc.tipo_ticket_id or any(
                        c["tipo"].id == dc.tipo_ticket_id and c["cantidad"] > 0
                        for c in carrito
                    ):
                        # consumimos un uso
                        from django.db.models import F
                        dc.usos_actuales = F("usos_actuales") + 1
                        dc.save(update_fields=["usos_actuales"])
            else:
                # 2) Si no es DiscountCode, probamos SharedPurchaseCode (cortesía)
                sc = (
                    SharedPurchaseCode.objects
                    .select_for_update()
                    .filter(code=promo_code, evento=evento, active=True)
                    .first()
                )
                if sc:
                    # Actualiza used_count según las entradas que usaron el código
                    confirmar_compra_con_shared_code(orden, sc, carrito)

        # Generar el código compartible N-1 para esta compra (si corresponde)
        finalizar_pago_y_generar_codigo(orden)

    success_url = f"/orders/public/checkout/success/{orden.id}/"
    return JsonResponse({"order_id": orden.id, "success_url": success_url}, status=201)



@csrf_exempt
def promo_validar(request):
    """
    Esqueleto mínimo para el validador de códigos.
    Hoy no aplica ninguna regla (si envías algo, lo marca válido= True).
    Ajustaremos aquí cuando conectemos tu modelo de descuentos/cortesías.
    """
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = {}

    code = (data.get("code") or "").strip()
    result = {
        "ok": bool(code),
        "code": code,
        "discount": 0,
        "type": "none",
        "message": "Código aceptado (placeholder)." if code else "Código vacío.",
    }
    return JsonResponse(result, status=200 if code else 400)

def shared_code_validate(request):
    code = request.POST.get('code', '').strip()
    evento_id = request.POST.get('evento_id')
    if not code or not evento_id:
        return HttpResponseBadRequest("Faltan parámetros")

    try:
        sc = SharedPurchaseCode.objects.get(code=code, evento_id=evento_id)
    except SharedPurchaseCode.DoesNotExist:
        return JsonResponse({"ok": False, "reason": "Código inexistente"}, status=404)

    return JsonResponse({
        "ok": sc.is_valid_now(),
        "remaining_uses": sc.remaining_uses,
        "max_uses": sc.max_uses,
        "message": (
            "Código válido" if sc.is_valid_now() else
            "Código sin usos disponibles o inactivo/expirado"
        )
    })


def validar_promocode(request):
    """
    Valida un código de descuento / cortesía contra el carrito actual.

    El front envía JSON:
      {
        "evento_slug": "...",
        "code": "CODIGO",
        "items": [
          {"tipo_ticket_id": 1, "cantidad": 2},
          ...
        ]
      }

    Respuesta esperada por el front:
      {
        "ok": true/false,
        "discount_amount": <int>,
        "message": "texto para mostrar"
      }
    """
    if request.method != "POST":
        return JsonResponse(
            {"ok": False, "message": "Método no permitido."},
            status=405,
        )

    # Leer JSON del body
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse(
            {"ok": False, "message": "Payload inválido."},
            status=400,
        )

    code = (data.get("code") or "").strip()
    evento_slug = (data.get("evento_slug") or "").strip()
    items = data.get("items") or []

    if not code or not evento_slug:
        return JsonResponse(
            {"ok": False, "message": "Faltan datos para validar el código."},
            status=400,
        )

    # Buscar evento
    event = get_object_or_404(Evento, slug=evento_slug)

    # Construimos carrito a partir de items
    # carrito = [{ 'tipo': TipoTicket, 'cantidad': int, 'precio_unitario': Decimal }, ...]
    if not isinstance(items, list) or not items:
        return JsonResponse(
            {"ok": False, "message": "No hay tickets en el carrito."},
            status=400,
        )

    # Mapear ids de tipo de ticket
    ids = set()
    for it in items:
        try:
            tt_id = int(it.get("tipo_ticket_id"))
            cantidad = int(it.get("cantidad") or 0)
        except Exception:
            continue
        if cantidad > 0:
            ids.add(tt_id)

    if not ids:
        return JsonResponse(
            {"ok": False, "message": "No hay tickets en el carrito."},
            status=400,
        )

    tipos_map = {
        t.id: t
        for t in TipoTicket.objects.filter(evento=event, id__in=ids)
    }

    carrito = []
    subtotal = Decimal("0")

    for it in items:
        try:
            tt_id = int(it.get("tipo_ticket_id"))
            cantidad = int(it.get("cantidad") or 0)
        except Exception:
            continue
        if cantidad <= 0:
            continue
        tt = tipos_map.get(tt_id)
        if not tt:
            continue
        price = Decimal(tt.precio)
        carrito.append({
            "tipo": tt,
            "cantidad": cantidad,
            "precio_unitario": price,
        })
        subtotal += price * cantidad

    if subtotal <= 0:
        return JsonResponse(
            {"ok": False, "message": "No hay tickets válidos en el carrito."},
            status=400,
        )

    # 1) Intentamos primero código de descuento manual (DiscountCode)
    dc = (
        DiscountCode.objects
        .filter(evento=event, codigo__iexact=code, activo=True)
        .first()
    )

    hoy = timezone.now().date()

    if dc:
        # Vigencia
        if dc.vigente_desde and hoy < dc.vigente_desde:
            return JsonResponse(
                {"ok": False, "message": "El código aún no está vigente."},
                status=400,
            )
        if dc.vigente_hasta and hoy > dc.vigente_hasta:
            return JsonResponse(
                {"ok": False, "message": "El código ya no está vigente."},
                status=400,
            )
        if dc.usos_maximos is not None and dc.usos_actuales >= dc.usos_maximos:
            return JsonResponse(
                {"ok": False, "message": "Este código alcanzó su límite de usos."},
                status=400,
            )

        # Si exige un tipo de ticket específico, validamos que esté en el carrito
        if dc.tipo_ticket_id:
            tiene_tipo = any(
                c["tipo"].id == dc.tipo_ticket_id and c["cantidad"] > 0
                for c in carrito
            )
            if not tiene_tipo:
                return JsonResponse(
                    {
                        "ok": False,
                        "message": "Este código requiere un tipo de ticket específico en el carrito.",
                    },
                    status=400,
                )

        # Descuento fijo en CLP, acotado al subtotal
        discount_amount = int(min(Decimal(dc.monto_descuento), subtotal))
        if discount_amount <= 0:
            return JsonResponse(
                {
                    "ok": False,
                    "message": "El código no genera descuento con este carrito.",
                    "discount_amount": 0,
                },
                status=400,
            )

        return JsonResponse(
            {
                "ok": True,
                "kind": "fixed",
                "discount_amount": discount_amount,
                "message": f"Código aplicado. Descuento de {discount_amount:,} CLP.",
            }
        )

    # 2) Si no es DiscountCode, probamos con código de cortesía SharedPurchaseCode
    sc = (
        SharedPurchaseCode.objects
        .filter(code=code, evento=event, active=True)
        .first()
    )

    if sc:
        # Usamos la función de servicio que ya calcula descuento N-1
        discount_decimal = aplicar_shared_code_en_carrito(carrito, sc)
        discount_amount = int(discount_decimal or 0)

        if discount_amount <= 0:
            return JsonResponse(
                {
                    "ok": False,
                    "kind": "shared",
                    "discount_amount": 0,
                    "message": "El código de cortesía no se puede aplicar a este carrito.",
                },
                status=400,
            )

        return JsonResponse(
            {
                "ok": True,
                "kind": "shared",
                "discount_amount": discount_amount,
                "message": "Código de cortesía aplicado.",
            }
        )

    # 3) Ningún código encontrado
    return JsonResponse(
        {"ok": False, "message": "El código ingresado no es válido."},
        status=404,
    )




def _count_non_parking_tickets(orden):
    return orden.tickets.filter(tipo__is_parking=False).count()

def finalizar_pago_y_generar_codigo(orden):
    n_tickets = _count_non_parking_tickets(orden)
    if n_tickets > 1:
        SharedPurchaseCode.objects.create(
            orden=orden,
            evento=orden.evento,
            max_uses=n_tickets - 1
        )
    return orden


def shared_code_validate(request):
    code = request.POST.get('code', '').strip()
    evento_id = request.POST.get('evento_id')
    if not code or not evento_id:
        return HttpResponseBadRequest("Faltan parámetros")

    try:
        sc = SharedPurchaseCode.objects.get(code=code, evento_id=evento_id)
    except SharedPurchaseCode.DoesNotExist:
        return JsonResponse({"ok": False, "reason": "Código inexistente"}, status=404)

    return JsonResponse({
        "ok": sc.is_valid_now(),
        "remaining_uses": sc.remaining_uses,
        "max_uses": sc.max_uses,
        "message": ("Código válido" if sc.is_valid_now() else "Sin usos o expirado")
    })


