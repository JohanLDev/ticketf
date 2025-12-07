from django.urls import path
from . import views
from . import views_pdf
from . import views_email
from . import views_analytics
from . import views_export
from . import views_reports
from . import views_operational
from . import views_public
from . import views_public_api



app_name = "orders"



urlpatterns = [
    path("", views.order_list, name="list"),
    path("crear/", views.order_create, name="create"),
    path("<int:pk>/", views.order_detail, name="detail"),
    path("ticket/<str:code>/qr.png", views.ticket_qr, name="ticket_qr"),
    path("validate/<str:code>/", views.validate_ticket, name="validate"),
    path("validar/", views.validator_page, name="validator"),
    path("tickets/<uuid:code>/pdf/", views_pdf.ticket_pdf_by_code, name="ticket-pdf"),
    path("tickets/<uuid:code>/email/", views_email.ticket_email_by_code, name="ticket-email"),
    path("orders/<int:order_id>/email-all/", views_email.order_email_all, name="order-email-all"),
    path("analytics/<int:event_id>/", views_analytics.event_summary, name="event-analytics"),
    path("analytics/<int:event_id>/export/", views_export.export_event_tickets_csv, name="event-export-csv"),
    path("analytics/<int:event_id>/summary-data/", views_analytics.event_summary_data, name="event-summary-data"),
    path("analytics/<int:event_id>/report.pdf", views_reports.event_report_pdf, name="event-report-pdf"),
    path("tickets/<int:ticket_id>/cancel/", views_operational.ticket_cancel, name="ticket-cancel"),
    path("tickets/<int:ticket_id>/reissue/", views_operational.ticket_reissue, name="ticket-reissue"),

    # Público (evento + compra)
    path("public/event/<slug:slug>/", views_public.event_public_detail, name="public-event"),
    path("public/event/<slug:slug>/comprar/", views_public.checkout_step1, name="public-checkout-step1"),
    path("api/checkout/", views_public_api.checkout_crear_orden, name="public-checkout-create"),
    path("public/checkout/success/<int:order_id>/", views_public.public_checkout_success, name="public-checkout-success"),
    path("public/checkout/<int:order_id>/pdf/", views_pdf.order_tickets_pdf, name="public-order-pdf"),
    path("public/event/<slug:slug>/comprar/datos/", views_public.checkout_step3_form, name="public-checkout-step3"),
    path("public/", views_public.home_public, name="public-home"),
    path('api/promo/validar/', views_public_api.validar_promocode, name='api-promo-validar'),  # <- deja esta
    path('public/checkout/pay/<slug:slug>/', views_public.public_checkout_pay, name='public-checkout-pay'),
    # si vas a usar el shared code:
    # path('api/shared-code/validate', views_public_api.shared_code_validate, name='shared_code_validate'),
    path('api/shared-code/validate/', views_public_api.shared_code_validate, name='shared_code_validate'),

    path("ticket/<uuid:code>/pdf/", views.ticket_pdf_by_user, name="ticket_pdf_user"),

    path(
        "analytics/<int:event_id>/financial/",
        views_reports.event_financial_report,
        name="event-financial-report",
    ),
    
    path(
        "events/<int:event_id>/orders/",
        views_operational.orders_by_event,
        name="orders-by-event",
    ),


    path( "public/<slug:slug>/checkout/webpay-return/", views_public.webpay_return, name="webpay-return",),
    
]