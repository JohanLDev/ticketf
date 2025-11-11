# tickets/views_discounts.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django import forms

from accounts.models import Cuenta           # <— usamos el modelo directo
from events.models import Evento
from tickets.models import TipoTicket, DiscountCode

# Fallback para resolver la cuenta actual SIN depender de accounts.utils
def _current_account(request):
    cid = request.session.get("cuenta_id")
    if cid:
        c = Cuenta.objects.filter(id=cid).first()
        if c:
            return c
    # Fallback: si el usuario solo tiene una, o toma la primera activa
    return Cuenta.objects.first()

class DiscountForm(forms.ModelForm):
    class Meta:
        model = DiscountCode
        fields = [
            "nombre", "codigo", "evento", "tipo_ticket",
            "monto_descuento", "usos_maximos",
            "vigente_desde", "vigente_hasta", "activo",
        ]
        widgets = {
            "vigente_desde": forms.DateInput(attrs={"type": "date"}),
            "vigente_hasta": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Inputs de texto / número
        for name in ["nombre", "codigo", "monto_descuento", "usos_maximos"]:
            self.fields[name].widget.attrs.update({"class": "form-control"})
        # Selects
        for name in ["evento", "tipo_ticket"]:
            self.fields[name].widget.attrs.update({"class": "form-select"})
        # Checkbox
        self.fields["activo"].widget.attrs.update({"class": "form-check-input"})


@login_required
def discounts_list(request):
    cuenta = _current_account(request)
    qs = DiscountCode.objects.filter(cuenta=cuenta).select_related("evento", "tipo_ticket")
    return render(request, "tickets/discounts_list.html", {"cuenta": cuenta, "items": qs})

@login_required
def discounts_create(request):
    cuenta = _current_account(request)

    form = DiscountForm(request.POST or None)
    form.fields["evento"].queryset = Evento.objects.filter(cuenta=cuenta)
    form.fields["tipo_ticket"].queryset = TipoTicket.objects.filter(evento__cuenta=cuenta)

    if request.method == "POST" and form.is_valid():
        d = form.save(commit=False)
        d.cuenta = cuenta
        vd, vh = d.vigente_desde, d.vigente_hasta
        if vd and vh and vd > vh:
            form.add_error("vigente_hasta", "La fecha de término debe ser posterior al inicio.")
        else:
            d.usos_actuales = 0
            d.save()
            return redirect("tickets:discounts_list")

    return render(request, "tickets/discounts_form.html", {"cuenta": cuenta, "form": form})
