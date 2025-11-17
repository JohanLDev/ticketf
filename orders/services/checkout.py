# orders/services/checkout.py
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from django.db.models import F
from orders.models import Orden, Ticket
from orders.models import SharedPurchaseCode
#from tickets.models import Discount

from decimal import Decimal


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



def _count_non_parking_tickets(orden):
    # Ajusta según tu modelo: asumiendo orden.tickets relaciona Ticket -> TipoTicket con flag is_parking
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


def aplicar_shared_code_en_carrito(carrito, shared_code):
    """
    carrito: lista de dicts con items:
        { 'tipo': TipoTicket, 'cantidad': int, 'precio_unitario': Decimal }
    Excluye tipo.is_parking.
    Retorna un Decimal con el total de descuento.
    """
    if not shared_code or not shared_code.is_valid_now():
        return Decimal('0')

    usos_disp = shared_code.remaining_uses
    if usos_disp <= 0:
        return Decimal('0')

    entradas = [i for i in carrito if not i['tipo'].is_parking and i['cantidad'] > 0]
    entradas.sort(key=lambda x: x['precio_unitario'], reverse=True)

    descuento_total = Decimal('0')
    usos_restantes = usos_disp

    for item in entradas:
        if usos_restantes <= 0:
            break
        aplicar_a = min(item['cantidad'], usos_restantes)
        descuento_total += item['precio_unitario'] * aplicar_a
        usos_restantes -= aplicar_a

    return descuento_total


def confirmar_compra_con_shared_code(orden, shared_code, carrito):
    """
    Llamar después de crear la orden y los tickets (durante confirmación).
    Actualiza el contador de usos del shared_code.
    """
    if not shared_code or not shared_code.is_valid_now():
        return

    usos_necesarios = 0
    entradas = [i for i in carrito if not i['tipo'].is_parking and i['cantidad'] > 0]
    entradas.sort(key=lambda x: x['precio_unitario'], reverse=True)

    usos_disp = shared_code.remaining_uses
    for item in entradas:
        if usos_disp <= 0:
            break
        aplica = min(item['cantidad'], usos_disp)
        usos_necesarios += aplica
        usos_disp -= aplica

    if usos_necesarios <= 0:
        return

    with transaction.atomic():
        sc = SharedPurchaseCode.objects.select_for_update().get(pk=shared_code.pk)
        puede = max(0, sc.max_uses - sc.used_count)
        aplica_final = min(puede, usos_necesarios)
        if aplica_final > 0:
            sc.used_count += aplica_final
            sc.save(update_fields=['used_count'])