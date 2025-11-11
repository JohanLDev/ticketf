# orders/services/checkout.py
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from orders.models import Orden, Ticket
#from tickets.models import Discount



def _get_discount_model():
    """
    Devuelve el modelo de descuentos del app 'tickets'.
    Primero intenta nombres comunes; si no, detecta por campos típicos.
    """
    # 1) nombres más comunes
    for model_name in ('Discount', 'TicketDiscount', 'Descuento', 'PromoCode', 'Promo'):
        try:
            return apps.get_model('tickets', model_name)
        except LookupError:
            pass

    # 2) autodetección por campos
    try:
        app = apps.get_app_config('tickets')
    except LookupError:
        return None

    required = {'codigo', 'evento', 'tipo_ticket', 'monto_descuento',
                'usos_actuales', 'usos_maximos', 'vigente_desde', 'vigente_hasta', 'activo'}
    for model in app.get_models():
        try:
            field_names = {f.name for f in model._meta.get_fields()}
        except Exception:
            continue
        if required.issubset(field_names):
            return model

    return None



def crear_orden_y_tickets(*, evento, comprador_email, items, created_by=None, promo_code=None):
    with transaction.atomic():
        orden = Orden.objects.create(
            cuenta=evento.cuenta,
            evento=evento,
            comprador_email=comprador_email,
        )

        tickets_creados = []
        for it in items:
            tt = it["tipo_ticket"]
            cantidad = int(it["cantidad"])
            if cantidad <= 0 or cantidad > 10:
                raise ValueError("Cantidad inválida para un tipo de ticket.")
            for _ in range(cantidad):
                tk = Ticket.objects.create(orden=orden, evento=evento, tipo=tt)
                tickets_creados.append(tk)

        _consumir_descuento(evento=evento, promo_code=promo_code)

        return orden, tickets_creados



def _consumir_descuento(*, evento, promo_code):
    if not promo_code:
        return

    Discount = _get_discount_model()
    if Discount is None:
        raise ValueError("No está configurado el modelo de descuentos.")

    hoy = timezone.now().date()
    d = (Discount.objects
         .select_for_update()
         .filter(evento=evento, codigo__iexact=promo_code, activo=True)
         .first())

    if not d:
        raise ValueError("El código ingresado no es válido.")
    if d.vigente_desde and hoy < d.vigente_desde:
        raise ValueError("El código aún no está vigente.")
    if d.vigente_hasta and hoy > d.vigente_hasta:
        raise ValueError("El código ya no está vigente.")
    if d.usos_maximos is not None and d.usos_actuales >= d.usos_maximos:
        raise ValueError("Este código ya fue utilizado o alcanzó su límite de usos.")

    d.usos_actuales = F('usos_actuales') + 1
    d.save(update_fields=['usos_actuales'])
