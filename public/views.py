from django.shortcuts import render
from events.models import Evento

def home(request):
    qs = Evento.objects.all()
    # si tienes un campo "estado" y quieres ocultar borradores/ocultos:
    try:
        qs = qs.exclude(estado__in=["borrador", "oculto", "draft", "hidden"])
    except Exception:
        pass
    # ordena por fecha si existe; si no, por id
    try:
        eventos = qs.order_by("-fecha_inicio")[:20]
    except Exception:
        eventos = qs.order_by("-id")[:20]

    return render(request, "public/home.html", {"eventos": eventos})