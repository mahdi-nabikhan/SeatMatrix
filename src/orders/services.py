import secrets
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from operations.models import Showtime,ShowtimeSeat
from orders.models import Order,Ticket
from promotions.services import apply_promotions
from orders.redis_locks import (
    HOLD_TTL_SECONDS,
    get_cart,
    get_locked_seats_map,
    hold_seats_in_redis,
    release_cart,
)




def _generate_order_number()-> str :
    timestamp = timezone.now().strftime('%y%m%d%H%M')
    random_part = secrets.token_hex(3).upper()
    return f"ORD-{timestamp}{random_part}"



def hold_showtime_seats (
    *,
    owner_id:str,
    showtime_id:int,
    showtime_seat_ids:list[int]) -> dict:
    if not showtime_seat_ids:
        raise ValidationError('حداقل یک صندلی باید انتخاب شود')
    
    
    unique_seat_ids = sorted(set(showtime_seat_ids))
    
    
    showtime = Showtime.objects.filter(id=showtime_id).first()
    if not showtime:
        raise ValidationError("سانس مورد نظر یافت نشد.")

    seats = list(ShowtimeSeat.objects.filter(showtime=showtime, id__in=unique_seat_ids))
    if len(seats) != len(unique_seat_ids):
        raise ValidationError("یک یا چند صندلی متعلق به این سانس نیست.")

    sold_ids = [s.id for s in seats if s.status == 'SOLD']
    if sold_ids:
        raise ValidationError(f"صندلی‌های زیر قبلاً فروخته شده‌اند: {sold_ids}")

    acquired = hold_seats_in_redis(
        owner_id=owner_id,
        showtime_id=showtime_id,
        seat_ids=unique_seat_ids,
    )
    if not acquired:
        raise ValidationError("یک یا چند صندلی انتخاب‌شده هم‌اکنون توسط کاربر دیگری رزرو شده است.")

    return {
        "showtime_id": showtime_id,
        "seat_ids": unique_seat_ids,
        "expires_in_seconds": HOLD_TTL_SECONDS,
        "estimated_total": showtime.base_price * len(unique_seat_ids),
    }
    



@transaction.atomic
def checkout_cart_to_order(*, customer, coupon_code: str | None = None) -> Order:
    owner_id = f"user:{customer.user_id}"
    cart = get_cart(owner_id)
    if not cart:
        raise ValidationError("سبد خرید شما خالی است یا مهلت رزرو صندلی‌ها به پایان رسیده است.")

    showtime_id = cart['showtime_id']
    seat_ids = sorted(cart['seat_ids'])

    locked_map = get_locked_seats_map(showtime_id=showtime_id, seat_ids=seat_ids)
    for sid in seat_ids:
        if locked_map.get(sid) != owner_id:
            raise ValidationError("مهلت رزرو یک یا چند صندلی به پایان رسیده است. لطفاً مجدداً انتخاب کنید.")

    showtime = Showtime.objects.filter(id=showtime_id).first()
    if not showtime:
        raise ValidationError("سانس مورد نظر یافت نشد.")

    seats = list(
        ShowtimeSeat.objects.select_for_update()
        .filter(showtime=showtime, id__in=seat_ids)
        .order_by('id')
    )
    if len(seats) != len(seat_ids):
        raise ValidationError("صندلی‌های انتخاب‌شده نامعتبر هستند.")

    already_unavailable = [s.id for s in seats if s.status != 'AVAILABLE']
    if already_unavailable:
        raise ValidationError(f"صندلی‌های زیر در دسترس نیستند: {already_unavailable}")

    total_amount = showtime.base_price * len(seats)

    promo_result = apply_promotions(
        total_amount=total_amount,
        showtime_start_time=showtime.start_time,
        coupon_code=coupon_code,
        consume=True,
    )
    discount_amount = promo_result['discount_amount']
    final_amount = promo_result['final_amount']

    is_free_order = final_amount == 0
    order = Order.objects.create(
        customer=customer,
        order_number=_generate_order_number(),
        status='PAID' if is_free_order else 'PENDING',
        total_amount=total_amount,
        discount_amount=discount_amount,
        final_amount=final_amount,
    )

    Ticket.objects.bulk_create([
        Ticket(
            order=order,
            showtime_seat=seat,
            price=showtime.base_price,
        )
        for seat in seats
    ])

    ShowtimeSeat.objects.filter(id__in=seat_ids).update(
        status='SOLD' if is_free_order else 'RESERVED'
    )

    transaction.on_commit(lambda: release_cart(owner_id))
    return order