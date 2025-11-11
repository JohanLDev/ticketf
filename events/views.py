from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from accounts.utils import get_current_cuenta, require_role
from .models import Evento

class EventoForm(forms.ModelForm):
    class Meta:
        model = Evento
        fields = ["nombre","estado","fecha_inicio","fecha_termino","ubicacion","banner_url"]

@require_role("admin","staff")
def event_list(request):
    cuenta = get_current_cuenta(request)
    qs = Evento.objects.filter(cuenta=cuenta)
    return render(request, "events/list.html", {"cuenta": cuenta, "eventos": qs})

@require_role("admin","staff")
def event_create(request):
    cuenta = get_current_cuenta(request)
    form = EventoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        e = form.save(commit=False)
        e.cuenta = cuenta
        e.save()
        return redirect("events:list")
    return render(request, "events/form.html", {"form": form, "title": "Crear evento"})

@require_role("admin","staff")
def event_edit(request, pk):
    cuenta = get_current_cuenta(request)
    obj = get_object_or_404(Evento, pk=pk, cuenta=cuenta)
    form = EventoForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("events:list")
    return render(request, "events/form.html", {"form": form, "title": "Editar evento"})

@require_role("admin","staff")
def event_delete(request, pk):
    cuenta = get_current_cuenta(request)
    obj = get_object_or_404(Evento, pk=pk, cuenta=cuenta)
    if request.method == "POST":
        obj.delete()
        return redirect("events:list")
    return render(request, "events/delete_confirm.html", {"obj": obj})
