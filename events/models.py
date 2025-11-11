from django.db import models
from accounts.models import Cuenta
from django.utils.text import slugify

ESTADOS = [("borrador","Borrador"),("activo","Activo"),("inactivo","Inactivo"),("cancelado","Cancelado")]

class Evento(models.Model):
    id = models.BigAutoField(primary_key=True)
    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name="eventos")
    nombre = models.CharField(max_length=160)
    slug = models.SlugField(max_length=170)
    estado = models.CharField(max_length=15, choices=ESTADOS, default="borrador")
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_termino = models.DateField(null=True, blank=True)
    ubicacion = models.CharField(max_length=200, blank=True)
    banner_url = models.URLField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cuenta", "slug")
        ordering = ("-creado_en",)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)[:170]
        super().save(*args, **kwargs)

    def __str__(self): return f"{self.nombre} ({self.cuenta.nombre})"
