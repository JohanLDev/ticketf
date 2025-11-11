from django.db import models
from events.models import Evento
from django.utils import timezone

ACCESS = [("un_dia","Un día"), ("todos_los_dias","Todos los días")]
REENTRY = [("ilimitado","Ilimitado"), ("una_vez_por_dia","Una vez por día")]

class TipoTicket(models.Model):
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE, related_name="tipos")
    nombre = models.CharField(max_length=120)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    access_policy = models.CharField(max_length=20, choices=ACCESS, default="un_dia")
    reentry_rule = models.CharField(max_length=20, choices=REENTRY, default="una_vez_por_dia")
    includes_congress = models.BooleanField(default=False)
    is_vip = models.BooleanField(default=False)
    is_free = models.BooleanField(default=False)
    valid_day = models.DateField(null=True, blank=True)  # si access_policy=un_dia (opcional)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    is_parking = models.BooleanField(default=False)

    class Meta:
        unique_together = ("evento", "nombre")
        ordering = ("-creado_en",)

    def __str__(self):
        return f"{self.nombre} · {self.evento.nombre}"


class DiscountCode(models.Model):
    cuenta = models.ForeignKey("accounts.Cuenta", on_delete=models.CASCADE, related_name="discount_codes")
    evento = models.ForeignKey("events.Evento", on_delete=models.CASCADE, related_name="discount_codes")

    nombre = models.CharField(max_length=120)
    codigo = models.CharField(max_length=50, unique=True)

    # Si se selecciona, exige que en el carrito exista al menos 1 de ese tipo
    tipo_ticket = models.ForeignKey("tickets.TipoTicket", null=True, blank=True,
                                    on_delete=models.CASCADE, related_name="discount_codes")

    # Monto fijo que se descuenta al total (en CLP)
    monto_descuento = models.PositiveIntegerField()

    usos_maximos = models.PositiveIntegerField(default=1)
    usos_actuales = models.PositiveIntegerField(default=0)

    vigente_desde = models.DateField(null=True, blank=True)
    vigente_hasta = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"

    def disponible(self) -> bool:
        if not self.activo:
            return False
        hoy = timezone.now().date()
        if self.vigente_desde and hoy < self.vigente_desde:
            return False
        if self.vigente_hasta and hoy > self.vigente_hasta:
            return False
        if self.usos_actuales >= self.usos_maximos:
            return False
        return True