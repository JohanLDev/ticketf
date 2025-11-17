from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),  
    path("legal/privacidad/", views.privacy_policy, name="privacy_policy"),
    path("legal/cookies/", views.cookie_policy, name="cookie_policy"),
    path("legal/terminos-de-uso/", views.terms_of_use, name="terms_of_use"),
    path("legal/proteccion-datos/", views.data_protection_law, name="data_protection_law"),
]