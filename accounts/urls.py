from django.urls import path
from . import views
from . import views_super
from .views_super import super_cuentas, super_crear_cuenta, super_asignar_admin
from .views_admin import select_account, admin_dashboard
from .views import LoginView, LogoutView, RegisterView

from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views

app_name = "accounts"

urlpatterns = [
    # LOGIN / LOGOUT / REGISTER
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),

    # REGISTRO NORMAL (CREAR CUENTA)
    path("registro/", views.register, name="register_normal"),

    # PERFIL CON TABS
    path("perfil/", views.profile_view, name="profile"),

    # PERFIL API
    path("api/profile/", views.profile_api, name="profile_api"),

    # TICKET DE USUARIO (DETALLE)
    path("ticket/<int:ticket_id>/", views.user_ticket_detail, name="user_ticket_detail"),

    # PÁGINAS SUPERADMIN
    path("super/cuentas/", super_cuentas, name="super_cuentas"),
    path("super/cuentas/crear/", super_crear_cuenta, name="super_crear_cuenta"),
    path("super/cuentas/<uuid:cuenta_id>/asignar-admin/", super_asignar_admin, name="super_asignar_admin"),

    # PANEL ADMIN
    path("admin/select-account/", select_account, name="select_account"),
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),

    path("super/cuentas/<uuid:cuenta_id>/admins/",views_super.ver_admins, name="ver_admins",),

    path( "super/cuentas/<uuid:cuenta_id>/admins/<uuid:rol_id>/eliminar/", views_super.eliminar_admin, name="eliminar_admin", ),

    path( "super/cuentas/<uuid:cuenta_id>/admins/<uuid:rol_id>/editar/", views_super.editar_admin, name="editar_admin",),


    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset_form.html",
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("accounts:password_reset_done"),
        ),
        name="password_reset",
    ),

    # 2) Pantalla que dice "te enviamos un correo"
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html",
        ),
        name="password_reset_done",
    ),

    # 3) Vista a la que llega el usuario desde el enlace del email
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("accounts:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),

    # 4) Pantalla final "Contraseña actualizada"
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),


    path("plan/", views.account_plan, name="account_plan"),
    path("plan/checkout/", views.account_plan_checkout, name="account_plan_checkout"),
    path("plan/live-heatmap/", views.premium_heatmap, name="premium_heatmap"),
    path("plan/reportes-premium/", views.premium_reports, name="premium_reports"),

]
