from celery import shared_task
from django_tenants.utils import schema_context
from notifications.services import send_ticket_purchase_notifications


@shared_task(name='notifications.tasks.send_order_confirmation_task')
def send_order_confirmation_task(schema_name: str, order_id: int) -> None:
    with schema_context(schema_name):
        send_ticket_purchase_notifications(order_id=order_id)