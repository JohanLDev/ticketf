import json
from django.shortcuts import render, get_object_or_404
from events.models import Evento
from tickets.models import TipoTicket
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from core.webpay import wb
from transbank.webpay.webpay_plus.transaction import Transaction
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from .models import Orden
from orders.services.checkout import finalizar_pago_y_generar_codigo
from django.contrib import messages



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




def public_checkout_success(request, order_id):
    orden = get_object_or_404(Orden, id=order_id)
    tickets = orden.tickets.select_related("tipo")

    contexto = {
        "orden": orden,
        "evento": orden.evento,
        "tickets": tickets,
    }
    return render(request, "orders/public_checkout_success.html", contexto)




def checkout_step3_form(request, slug):
    event = get_object_or_404(Evento, slug=slug)

    buyer = None
    if request.user.is_authenticated:
        u = request.user
        profile = getattr(u, "profile", None)

        buyer = {
            # Datos personales
            "nombres": getattr(profile, "nombres", "") or getattr(u, "first_name", ""),
            "apellido1": getattr(profile, "apellido1", "") or getattr(u, "last_name", ""),
            "apellido2": getattr(profile, "apellido2", ""),

            # Email
            "email": u.email or "",
            "email2": u.email or "",

            # Teléfono
            "telefono": getattr(profile, "telefono_movil", ""),

            # Documento (si los tienes en el perfil)
            "doc_tipo": (getattr(profile, "tipo_doc", "") or "RUT").lower(),  # "rut" o "passport"
            "documento": getattr(profile, "numero_documento", ""),

            # Ubicación
            "pais": getattr(profile, "pais", "") or "CL",
            "region": getattr(profile, "region", ""),
            "ciudad": getattr(profile, "ciudad", ""),
            "comuna": getattr(profile, "comuna", ""),

            # Empresa / cargo / rubro (si existen en el perfil)
            "empresa": getattr(profile, "empresa", ""),
            "cargo": getattr(profile, "cargo", ""),
            "rubro": getattr(profile, "rubro", ""),
        }

    context = {
        "event": event,
        # lo mandamos como JSON al template
        "buyer_json": json.dumps(buyer) if buyer else "null",
    }
    return render(request, "orders/public_checkout_step3.html", context)


def public_checkout_pay(request, slug):
    """
    Inicia el pago con Webpay (ambiente de integración).

    Aquí armamos un payload mínimo en sesión para que webpay_return
    pueda finalizar la orden usando finalizar_pago_y_generar_codigo(...)
    """
    evento = get_object_or_404(Evento, slug=slug)

    # Por ahora: 1 ticket del primer tipo activo del evento (modo demo)
    tipo = (
        TipoTicket.objects
        .filter(evento=evento, activo=True)
        .order_by("precio")
        .first()
    )
    if not tipo:
        messages.error(request, "No hay tipos de ticket configurados para este evento.")
        return redirect("orders:public-checkout-step1", slug=slug)

    # De momento usamos SIEMPRE 1 ticket de ese tipo (como tenías en la versión inicial)
    cantidad = 1
    precio_unitario = int(tipo.precio)
    total = precio_unitario * cantidad

    # --- Guardamos en sesión lo que webpay_return espera ---
    payload = {
        "items": [
            {
                "tipo_ticket_id": tipo.id,
                "cantidad": cantidad,
                "precio_unitario": precio_unitario,
                "nombre": tipo.nombre,
            }
        ],
        "subtotal": total,
        "discount": 0,
        "total": total,
        "promo_code": None,
    }

        # Intentamos usar el email que viene del formulario (Step 3)
    email_form = request.POST.get("email")

    email = (
        email_form
        or (request.user.email if request.user.is_authenticated else None)
        or "demo@ticket-f.cl"
    )

    buyer = {
        "email": email,
        "nombres": getattr(request.user, "first_name", "") or "Comprador",
        "apellido1": getattr(request.user, "last_name", "") or "",
    }


    request.session["checkout_payload"] = payload
    request.session["checkout_buyer"] = buyer
    request.session.modified = True

    # --- Monto que se envía a Webpay: el total del payload ---
    amount = total

    # Identificadores únicos requeridos por Webpay
    buy_order = f"EVT{evento.id}-{int(timezone.now().timestamp())}"
    session_id = f"sess-{request.session.session_key or 'anon'}"

    # URL a la que Webpay volverá después del pago
    return_url = request.build_absolute_uri(
        reverse("orders:webpay-return", kwargs={"slug": slug})
    )

    # Llamamos al SDK de Webpay (ambiente TEST)
    resp = wb().create(
        buy_order=buy_order,
        session_id=session_id,
        amount=amount,
        return_url=return_url,
    )

    token = resp["token"]
    url = resp["url"]

    # Redirigimos al formulario de Webpay con el token_ws
    return redirect(f"{url}?token_ws={token}")





@csrf_exempt
def webpay_return(request, slug):
    # 1. Obtener token entregado por Webpay
    token = request.GET.get("token_ws") or request.POST.get("token_ws")
    evento = get_object_or_404(Evento, slug=slug)

    if not token:
        messages.error(request, "No se recibió el token de Webpay.")
        return render(
            request,
            "orders/public_checkout_error.html",
            {
                "event": evento,
                "reason": "missing-token",
            },
        )

    # 2. Confirmar la transacción en Webpay
    try:
        tx = wb().commit(token)   # tx es un dict
    except Exception as e:
        # Cualquier error técnico hablando con Webpay cae acá
        messages.error(request, "Error al confirmar el pago en Webpay.")
        return render(
            request,
            "orders/public_checkout_error.html",
            {
                "event": evento,
                "reason": "webpay-error",
                "detail": str(e),
            },
        )

    # 3. Validar respuesta de Webpay
    if tx.get("response_code") != 0 or tx.get("status") != "AUTHORIZED":
        messages.error(request, "Pago rechazado o no autorizado por Webpay.")
        return render(
            request,
            "orders/public_checkout_error.html",
            {
                "event": evento,
                "reason": "not-authorized",
                "detail": tx,
            },
        )

    # 4. Recuperar datos que guardamos en sesión en public_checkout_pay
    payload = request.session.pop("checkout_payload", None)
    buyer = request.session.pop("checkout_buyer", None)

    if not payload or not buyer:
        messages.error(request, "No encontramos los datos de la compra en la sesión.")
        return render(
            request,
            "orders/public_checkout_error.html",
            {
                "event": evento,
                "reason": "missing-session",
            },
        )

    cuenta = evento.cuenta

    # 5. Armar info de Webpay para guardar en la orden
    webpay_data = {
        "token": token,
        "authorization_code": tx.get("authorization_code"),
        "amount": tx.get("amount"),
        "buy_order": tx.get("buy_order"),
        "session_id": tx.get("session_id"),
        "card_last4": (tx.get("card_detail") or {}).get("card_number"),
    }

    # 6. Crear la orden definitiva y generar códigos de ticket
    orden = finalizar_pago_y_generar_codigo(
        evento=evento,
        payload=payload,
        buyer=buyer,
        webpay_data=webpay_data
    )
    # 7. Enviar al “compra exitosa” que ya tenías hecho
    return redirect("orders:public-checkout-success", order_id=orden.id)