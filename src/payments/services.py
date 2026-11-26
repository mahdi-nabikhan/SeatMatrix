from django.db import transaction
from rest_framework.exceptions import ValidationError

from operations.models import ShowtimeSeat
from orders.models import Order, Ticket
from payments.gateways import GatewayError, ZarinpalGateway
from payments.models import Transaction


def _release_order_seats(order: Order) -> None:
    
    seat_ids = list(order.tickets.values_list('showtime_seat_id', flat=True))
    order.tickets.all().delete()
    if seat_ids:
        ShowtimeSeat.objects.filter(id__in=seat_ids).update(status='AVAILABLE')


def initiate_payment(*, order: Order, callback_url: str, gateway: ZarinpalGateway | None = None) -> dict:
    if order.status != 'PENDING':
        raise ValidationError({'detail': 'این سفارش در وضعیت انتظار پرداخت نیست.'})

    if order.final_amount <= 0:
        raise ValidationError({'detail': 'مبلغ این سفارش صفر است و نیازی به درگاه پرداخت ندارد.'})

    gw = gateway or ZarinpalGateway()
    tx = Transaction.objects.create(
        order=order,
        amount=order.final_amount,
        status='PENDING',
        gateway_name='ZarinPal',
    )

    try:
        res = gw.request_payment(
            amount=order.final_amount,
            callback_url=callback_url,
            description=f'پرداخت سفارش {order.order_number}',
            email=getattr(order.customer.user, 'email', None) or None,
        )
    except GatewayError as exc:
        tx.status = 'FAILED'
        tx.response_code = exc.code
        tx.response_message = exc.message
        tx.save(update_fields=['status', 'response_code', 'response_message', 'updated_at'])
        raise ValidationError({'detail': exc.message})

    tx.authority = res['authority']
    tx.response_code = res['code']
    tx.response_message = res['message']
    tx.save(update_fields=['authority', 'response_code', 'response_message', 'updated_at'])

    return {
        'transaction': tx,
        'authority': res['authority'],
        'payment_url': res['payment_url'],
    }


@transaction.atomic
def verify_payment(
    *,
    authority: str,
    gateway_status: str,
    gateway: ZarinpalGateway | None = None,
) -> Transaction:
    tx = (
        Transaction.objects.select_for_update()
        .select_related('order')
        .filter(authority=authority)
        .first()
    )
    if not tx:
        raise ValidationError({'detail': 'تراکنش با این شناسه یافت نشد.'})

    # Idempotency: اگر کاربر صفحه کال‌بک را چند بار رفرش کرد
    if tx.status == 'SUCCESS':
        return tx

    order = Order.objects.select_for_update().get(pk=tx.order_id)

   
    if gateway_status != 'OK':
        tx.status = 'FAILED'
        tx.response_code = 'CANCELLED_BY_USER'
        tx.response_message = 'پرداخت توسط کاربر لغو شد یا ناموفق بود.'
        tx.save(update_fields=['status', 'response_code', 'response_message', 'updated_at'])

        if order.status == 'PENDING':
            order.status = 'CANCELLED'
            order.save(update_fields=['status', 'updated_at'])
            _release_order_seats(order)

        return tx

    gw = gateway or ZarinpalGateway()
    try:
        result = gw.verify_payment(amount=tx.amount, authority=authority)
    except GatewayError as exc:
        tx.status = 'FAILED'
        tx.response_code = exc.code
        tx.response_message = exc.message
        tx.save(update_fields=['status', 'response_code', 'response_message', 'updated_at'])

        if order.status == 'PENDING':
            order.status = 'CANCELLED'
            order.save(update_fields=['status', 'updated_at'])
            _release_order_seats(order)

        return tx

    if result['success']:
        tx.status = 'SUCCESS'
        tx.ref_id = result['ref_id']
        tx.card_pan = result['card_pan']
        tx.response_code = result['code']
        tx.response_message = result['message']
        tx.save(update_fields=['status', 'ref_id', 'card_pan', 'response_code', 'response_message', 'updated_at'])

        order.status = 'PAID'
        order.save(update_fields=['status', 'updated_at'])

        seat_ids = list(order.tickets.values_list('showtime_seat_id', flat=True))
        if seat_ids:
            ShowtimeSeat.objects.filter(id__in=seat_ids).update(status='SOLD')
    else:
        tx.status = 'FAILED'
        tx.response_code = result['code']
        tx.response_message = result['message']
        tx.save(update_fields=['status', 'response_code', 'response_message', 'updated_at'])

        if order.status == 'PENDING':
            order.status = 'CANCELLED'
            order.save(update_fields=['status', 'updated_at'])
            _release_order_seats(order)

    return tx