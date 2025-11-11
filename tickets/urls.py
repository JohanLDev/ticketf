from django.urls import path
from . import views
from . import views_discounts

app_name = "tickets"


urlpatterns = [
    path("<int:event_id>/", views.type_list, name="list"),
    path("<int:event_id>/crear/", views.type_create, name="create"),
    path("<int:event_id>/<int:pk>/editar/", views.type_edit, name="edit"),
    path("<int:event_id>/<int:pk>/eliminar/", views.type_delete, name="delete"),
    path("<int:event_id>/json/", views.tipos_json, name="tipos-json"),
    path("descuentos/", views_discounts.discounts_list, name="discounts_list"),
    path("descuentos/crear/", views_discounts.discounts_create, name="discounts_create"),

]
