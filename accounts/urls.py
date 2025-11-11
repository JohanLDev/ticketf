from django.urls import path
from .views import LoginView, LogoutView, RegisterView
from .views_super import super_cuentas, super_crear_cuenta, super_asignar_admin
from .views_admin import select_account, admin_dashboard

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),

    path("super/cuentas/", super_cuentas, name="super_cuentas"),
    path("super/cuentas/crear/", super_crear_cuenta, name="super_crear_cuenta"),
    path("super/cuentas/<uuid:cuenta_id>/asignar-admin/", super_asignar_admin, name="super_asignar_admin"),
]

urlpatterns += [
    path("admin/select-account/", select_account, name="select_account"),
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),
]