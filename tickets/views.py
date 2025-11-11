from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from accounts.utils import get_current_cuenta, require_role
from events.models import Evento
from .models import TipoTicket
from django.http import JsonResponse
from django.views.decorators.http import require_GET

class TipoForm(forms.ModelForm):
    class Meta:
        model = TipoTicket
        fields = ["nombre","precio","access_policy","reentry_rule","includes_congress","is_vip","is_free","valid_day","is_parking","activo"]

def _evento_del_tenant(request, event_id):
    cuenta = get_current_cuenta(request)
    return get_object_or_404(Evento, pk=event_id, cuenta=cuenta)

@require_role("admin","staff")
def type_list(request, event_id):
    evento = _evento_del_tenant(request, event_id)
    return render(request, "tickets/list.html", {"evento": evento, "tipos": evento.tipos.all()})

@require_role("admin","staff")
def type_create(request, event_id):
    evento = _evento_del_tenant(request, event_id)
    form = TipoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        t = form.save(commit=False); t.evento = evento; t.save()
        return redirect("tickets:list", event_id=evento.id)
    return render(request, "tickets/form.html", {"form": form, "evento": evento, "title": "Crear tipo"})

@require_role("admin","staff")
def type_edit(request, event_id, pk):
    evento = _evento_del_tenant(request, event_id)
    obj = get_object_or_404(TipoTicket, pk=pk, evento=evento)
    form = TipoForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save(); return redirect("tickets:list", event_id=evento.id)
    return render(request, "tickets/form.html", {"form": form, "evento": evento, "title": "Editar tipo"})

@require_role("admin","staff")
def type_delete(request, event_id, pk):
    evento = _evento_del_tenant(request, event_id)
    obj = get_object_or_404(TipoTicket, pk=pk, evento=evento)
    if request.method == "POST":
        obj.delete(); return redirect("tickets:list", event_id=evento.id)
    return render(request, "tickets/delete_confirm.html", {"obj": obj, "evento": evento})

@require_GET
def tipos_json(request, event_id):
    from accounts.utils import get_current_cuenta
    cuenta = get_current_cuenta(request)
    evento = get_object_or_404(Evento, pk=event_id, cuenta=cuenta)
    data = [{"id": t.id, "nombre": t.nombre} for t in evento.tipos.filter(activo=True)]
    return JsonResponse(data, safe=False)