from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django_tenants.utils import schema_context

from cinemas.models import Cinema
from operations.models import ShowtimeSeat
from orders.models import Order
from payments.models import Transaction


@shared_task(name='orders.tasks.cancel_expired_pending_orders')
def cancel_expired_pending_orders(expiration_minutes: int = 15) -> dict:
    cutoff = timezone.now() - timedelta(minutes=expiration_minutes)
    total_cancelled = 0

    tenants = Cinema.objects.exclude(schema_name='public').only('schema_name')
    for tenant in tenants:
        with schema_context(tenant.schema_name):
            expired_ids = list(
                Order.objects.filter(status='PENDING', created_at__lt=cutoff).values_list('id', flat=True)
            )
            for order_id in expired_ids:
                with transaction.atomic():
                    order = Order.objects.select_for_update().filter(id=order_id).first()
                    if not order or order.status != 'PENDING':
                        continue

                    order.status = 'CANCELLED'
                    order.save(update_fields=['status', 'updated_at'])

                    Transaction.objects.filter(order=order, status='PENDING').update(
                        status='FAILED',
                        response_code='EXPIRED_TIMEOUT',
                        response_message='مهلت پرداخت سفارش به پایان رسید.',
                        updated_at=timezone.now(),
                    )

                    seat_ids = list(order.tickets.values_list('showtime_seat_id', flat=True))
                    order.tickets.all().delete()
                    if seat_ids:
                        ShowtimeSeat.objects.filter(id__in=seat_ids).update(status='AVAILABLE')

                    total_cancelled += 1

    return {'cancelled_orders': total_cancelled}