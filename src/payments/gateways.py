from decimal import Decimal
import requests
from django.conf import settings


class GatewayError(Exception):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = str(code) if code is not None else None


class ZarinpalGateway:

    def __init__(self):
        self.merchant_id = settings.ZARINPAL_MERCHANT_ID
        self.sandbox = settings.ZARINPAL_SANDBOX
        self.currency = getattr(settings, 'ZARINPAL_CURRENCY', 'IRT')

        base = 'https://sandbox.zarinpal.com' if self.sandbox else 'https://payment.zarinpal.com'
        self.request_url = f'{base}/pg/v4/payment/request.json'
        self.verify_url = f'{base}/pg/v4/payment/verify.json'
        self.startpay_url = f'{base}/pg/StartPay/'

    def request_payment(
        self,
        *,
        amount: Decimal,
        callback_url: str,
        description: str,
        email: str | None = None,
        mobile: str | None = None,
    ) -> dict:
        payload = {
            'merchant_id': self.merchant_id,
            'amount': int(amount),
            'callback_url': callback_url,
            'description': description,
            'currency': self.currency,
        }
        metadata = {}
        if email:
            metadata['email'] = email
        if mobile:
            metadata['mobile'] = mobile
        if metadata:
            payload['metadata'] = metadata

        try:
            response = requests.post(self.request_url, json=payload, timeout=15)
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise GatewayError(f'خطا در ارتباط با درگاه پرداخت: {exc}')

        data = body.get('data') or {}
        errors = body.get('errors') or {}

        if data.get('code') == 100 and data.get('authority'):
            authority = data['authority']
            return {
                'authority': authority,
                'payment_url': f'{self.startpay_url}{authority}',
                'code': str(data['code']),
                'message': data.get('message', 'Success'),
            }

        err_code = errors.get('code') if isinstance(errors, dict) else None
        err_msg = errors.get('message') if isinstance(errors, dict) else str(errors)
        raise GatewayError(err_msg or 'درخواست پرداخت توسط درگاه رد شد.', code=err_code)

    def verify_payment(self, *, amount: Decimal, authority: str) -> dict:
        payload = {
            'merchant_id': self.merchant_id,
            'amount': int(amount),
            'authority': authority,
        }

        try:
            response = requests.post(self.verify_url, json=payload, timeout=15)
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise GatewayError(f'خطا در تایید تراکنش با درگاه: {exc}')

        data = body.get('data') or {}
        errors = body.get('errors') or {}
        code = data.get('code')

        
        if code in (100, 101):
            return {
                'success': True,
                'code': str(code),
                'ref_id': str(data.get('ref_id', '')),
                'card_pan': data.get('card_pan') or '',
                'message': data.get('message', 'Verified'),
            }

        err_code = errors.get('code') if isinstance(errors, dict) else code
        err_msg = errors.get('message') if isinstance(errors, dict) else str(errors)
        return {
            'success': False,
            'code': str(err_code) if err_code is not None else '',
            'ref_id': None,
            'card_pan': None,
            'message': err_msg or 'تراکنش تایید نشد.',
        }