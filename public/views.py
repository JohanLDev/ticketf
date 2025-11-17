from django.shortcuts import render
from events.models import Evento

def home(request):
    # Solo eventos publicados
    eventos = (
        Evento.objects
        .filter(estado="activo")
        .order_by("fecha_inicio")
    )
    return render(request, "public/home.html", {"eventos": eventos})

def privacy_policy(request):
    return render(request, "public/privacy_policy.html")

def cookie_policy(request):
    return render(request, "public/cookie_policy.html")

def terms_of_use(request):
    return render(request, "public/terms_of_use.html")

def data_protection_law(request):
    return render(request, "public/data_protection_law.html")