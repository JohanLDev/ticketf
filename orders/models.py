import uuid
from django.db import models
from accounts.models import Cuenta
from events.models import Evento
from tickets.models import TipoTicket
from django.conf import settings
from django.utils import timezone

ESTADO_TICKET = [("disponible","Disponible"), ("quemado","Quemado"), ("anulado", "Anulado")]

class Orden(models.Model):
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name="ordenes")
    evento = models.ForeignKey(Evento, on_delete=models.PROTECT, related_name="ordenes")
    comprador_email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Orden #{self.id} · {self.evento.nombre}"

class Ticket(models.Model):
    orden = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name="tickets")
    evento = models.ForeignKey(Evento, on_delete=models.PROTECT, related_name="tickets")
    tipo = models.ForeignKey(TipoTicket, on_delete=models.PROTECT, related_name="tickets")
    #code = models.CharField(max_length=36, unique=True, db_index=True)  # UUID
    code = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    estado = models.CharField(max_length=20, choices=ESTADO_TICKET, default="disponible")
    used_at = models.DateTimeField(null=True, blank=True)
    asistente_email = models.EmailField(blank=True)
    replaced_by = models.OneToOneField("self",null=True,blank=True,on_delete=models.SET_NULL,related_name="replaces",
)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tipo.nombre} · {self.code}"


class TicketActionLog(models.Model):
    ticket = models.ForeignKey("Ticket", related_name="action_logs", on_delete=models.CASCADE)
    action = models.CharField(max_length=30)  # "anular" | "reemitir" | "reenviar"
    reason = models.CharField(max_length=255, blank=True, default="")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} · {self.action} · ticket #{self.ticket_id}"



class AccessPoint(models.Model):
    """Puerta / torniquete / zona de control."""
    cuenta = models.ForeignKey('accounts.Cuenta', on_delete=models.CASCADE, related_name='access_points')
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('cuenta', 'nombre')
        ordering = ('nombre',)

    def __str__(self):
        return f'{self.nombre} ({self.cuenta.nombre})'


class AccessRole(models.Model):
    """Permisos por puerta: qué usuario puede validar en qué access point."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    access_point = models.ForeignKey(AccessPoint, on_delete=models.CASCADE, related_name='roles')
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('usuario', 'access_point')


RESULT = [
    ('OK', 'OK'),
    ('ALREADY_USED', 'ALREADY_USED'),
    ('NOT_FOUND', 'NOT_FOUND'),
    ('DENIED', 'DENIED'),
]

class ValidationLog(models.Model):
    """Bitácora de validaciones."""
    cuenta = models.ForeignKey('accounts.Cuenta', on_delete=models.CASCADE, related_name='validation_logs')
    evento = models.ForeignKey('events.Evento', on_delete=models.SET_NULL, null=True, blank=True)
    ticket = models.ForeignKey('orders.Ticket', on_delete=models.SET_NULL, null=True, blank=True)
    access_point = models.ForeignKey(AccessPoint, on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    result = models.CharField(max_length=16, choices=RESULT)
    note = models.CharField(max_length=160, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)


class PromoCode(models.Model):
    TIPOS = [
        ('percent', 'Porcentaje'),
        ('fixed', 'Monto fijo'),
    ]

    cuenta = models.ForeignKey("accounts.Cuenta", on_delete=models.CASCADE, related_name="promocodes")
    evento = models.ForeignKey("events.Evento", on_delete=models.CASCADE, related_name="promocodes")
    codigo = models.CharField(max_length=50, unique=True)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    valor = models.PositiveIntegerField(help_text="Porcentaje o monto fijo en CLP según tipo.")
    usos_maximos = models.PositiveIntegerField(default=1)
    usos_actuales = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    valido_desde = models.DateField(null=True, blank=True)
    valido_hasta = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.codigo} ({self.evento.nombre})"

    @property
    def disponible(self):
        """Retorna True si puede usarse."""
        hoy = timezone.now().date()
        if not self.activo:
            return False
        if self.valido_desde and hoy < self.valido_desde:
            return False
        if self.valido_hasta and hoy > self.valido_hasta:
            return False
        if self.usos_actuales >= self.usos_maximos:
            return False
        return True

    def registrar_uso(self):
        """Incrementa usos cuando una orden pagada lo aplica."""
        self.usos_actuales = models.F('usos_actuales') + 1
        self.save(update_fields=['usos_actuales'])