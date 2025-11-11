from django.urls import path
from . import views
app_name = "events"

urlpatterns = [
    path("", views.event_list, name="list"),
    path("crear/", views.event_create, name="create"),
    path("<int:pk>/editar/", views.event_edit, name="edit"),
    path("<int:pk>/eliminar/", views.event_delete, name="delete"),
]
