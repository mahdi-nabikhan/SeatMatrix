from django.utils import timezone
from notifications.models import InAppNotification, SMSLog
from notifications.providers import get_sms_provider
from orders.models import Order


def send_ticket_purchase_notifications(*, order_id: int) -> None:
    order = (
        Order.objects.select_related('customer__user')
        .prefetch_related(
            'tickets__showtime_seat__seat',
            'tickets__showtime_seat__showtime__movie',
        )
        .filter(id=order_id, status='PAID')
        .first()
    )
    if not order:
        return

    tickets = list(order.tickets.all())
    if not tickets:
        return

    first_showtime = tickets[0].showtime_seat.showtime
    movie_title = first_showtime.movie.title
    local_time = timezone.localtime(first_showtime.start_time).strftime('%Y-%m-%d %H:%M')
    seats_str = ', '.join(
        f'{t.showtime_seat.seat.row_label}{t.showtime_seat.seat.seat_number}'
        for t in tickets
    )
    ticket_codes = ', '.join(str(t.ticket_code)[:8].upper() for t in tickets)

    title = f'تایید خرید بلیت فیلم {movie_title}'
    message = (
        f'سفارش {order.order_number} با موفقیت نهایی شد.\n'
        f'فیلم: {movie_title} | سانس: {local_time}\n'
        f'صندلی‌ها: {seats_str}\n'
        f'کد بلیت‌ها: {ticket_codes}'
    )

    user = order.customer.user
    InAppNotification.objects.create(
        user=user,
        title=title,
        message=message,
    )

    phone = getattr(user, 'phone_number', None) or getattr(order.customer, 'phone_number', None)
    if phone:
        provider = get_sms_provider()
        sms_log = SMSLog.objects.create(
            phone_number=phone,
            message=message,
            provider=provider.name,
            status='PENDING',
        )
        result = provider.send(phone_number=phone, message=message)
        sms_log.status = 'SENT' if result['success'] else 'FAILED'
        sms_log.provider_response = result['response']
        sms_log.save(update_fields=['status', 'provider_response'])