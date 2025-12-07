# core/webpay.py

from transbank.webpay.webpay_plus.transaction import Transaction
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType

# Credenciales de INTEGRACIÓN Webpay Plus (REST)
WEBPAY_COMMERCE_CODE = "597055555532"
WEBPAY_API_KEY = "579B532A7440BB0C9079DED94D31EA1615BACEB56610332264630D42D0A36B1C"

def wb() -> Transaction:
    """
    Retorna una instancia de Transaction configurada para el ambiente de integración.
    """
    options = WebpayOptions(
        commerce_code=WEBPAY_COMMERCE_CODE,
        api_key=WEBPAY_API_KEY,
        integration_type=IntegrationType.TEST,  # importante: ambiente de integración
    )
    return Transaction(options)