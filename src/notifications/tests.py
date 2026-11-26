from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_redis import get_redis_connection
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.test import APIClient

from cinemas.models import Cinema, CinemaDomain, Movie
from operations.models import Address, CinemaBranch, Hall, Seat, Showtime, ShowtimeSeat
from orders.models import Order, Ticket
from orders.redis_locks import cart_key, release_cart, seat_lock_key
from orders.services import checkout_cart_to_order, hold_showtime_seats
from orders.tasks import cancel_expired_pending_orders
from payments.models import Transaction
from profiles.models import Customer

User = get_user_model()


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class NotificationAndCleanupTaskTests(TransactionTestCase):
    def setUp(self):
        connection.set_schema_to_public()

        self.tenant = Cinema.objects.create(
            schema_name='test_cinema_notif',
            name='Test Cinema Notif',
        )
        self.domain = CinemaDomain.objects.create(
            domain='notiftest.lvh.me',
            tenant=self.tenant,
            is_primary=True,
        )

        self.user = User.objects.create_user(
            username='notif_customer',
            email='notif_customer@example.com',
            password='StrongPassword123!',
        )
        self.customer = Customer.objects.create(
            user=self.user,
            firstname='Mahdi',
            last_name='Notif',
        )
        self.movie = Movie.objects.create(
            title='Dune',
            description='Sci-fi epic',
            duration_minutes=155,
        )

        connection.set_tenant(self.tenant)

        self.address = Address.objects.create(
            province='Tehran',
            city='Tehran',
            full_address='Jordan St',
        )
        self.branch = CinemaBranch.objects.create(
            address=self.address,
            branch_name='Cinema Farhang',
        )
        self.hall = Hall.objects.create(
            branch=self.branch,
            name='Hall 3',
            capacity=30,
        )
        self.seat_1 = Seat.objects.create(hall=self.hall, row_label='C', seat_number=1)
        self.seat_2 = Seat.objects.create(hall=self.hall, row_label='C', seat_number=2)
        self.showtime = Showtime.objects.create(
            hall=self.hall,
            movie=self.movie,
            start_time=timezone.now() + timedelta(hours=4),
            base_price=180000,
        )
        self.ss_1, _ = ShowtimeSeat.objects.get_or_create(showtime=self.showtime, seat=self.seat_1)
        self.ss_2, _ = ShowtimeSeat.objects.get_or_create(showtime=self.showtime, seat=self.seat_2)

        self.client = APIClient(HTTP_HOST=self.domain.domain)
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        connection.set_tenant(self.tenant)
        redis_conn = get_redis_connection('default')
        owner = f'user:{self.user.id}'
        release_cart(owner)
        redis_conn.delete(cart_key(owner))
        redis_conn.delete(seat_lock_key(self.showtime.id, self.ss_1.id))
        redis_conn.delete(seat_lock_key(self.showtime.id, self.ss_2.id))

        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{self.tenant.schema_name}" CASCADE')

    @patch('payments.gateways.ZarinpalGateway.verify_payment')
    @patch('payments.gateways.ZarinpalGateway.request_payment')
    def test_payment_verify_creates_in_app_notification_and_mark_read(self, mock_request, mock_verify):
        mock_request.return_value = {
            'authority': 'S00000000000000000000000000000077777',
            'payment_url': 'https://sandbox.zarinpal.com/pg/StartPay/S00000000000000000000000000000077777',
            'code': '100',
            'message': 'Success',
        }
        mock_verify.return_value = {
            'success': True,
            'code': '100',
            'ref_id': '11223344',
            'card_pan': '603799******9999',
            'message': 'Verified',
        }

        with schema_context(self.tenant.schema_name):
            hold_showtime_seats(
                owner_id=f'user:{self.user.id}',
                showtime_id=self.showtime.id,
                showtime_seat_ids=[self.ss_1.id],
            )
            order = checkout_cart_to_order(customer=self.customer)

        self.client.post(
            reverse('payment-request'),
            {'order_number': order.order_number},
            format='json',
        )
        verify_url = reverse('payment-verify')
        ver_res = self.client.get(
            f"{verify_url}?Authority=S00000000000000000000000000000077777&Status=OK"
        )
        self.assertEqual(ver_res.status_code, status.HTTP_200_OK)

        list_res = self.client.get(reverse('notification-list'))
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(list_res.data['unread_count'], 1)
        self.assertEqual(len(list_res.data['results']), 1)
        notif_id = list_res.data['results'][0]['id']
        self.assertIn('Dune', list_res.data['results'][0]['title'])

        read_res = self.client.post(reverse('notification-read', kwargs={'pk': notif_id}))
        self.assertEqual(read_res.status_code, status.HTTP_200_OK)
        self.assertTrue(read_res.data['is_read'])

        list_after = self.client.get(reverse('notification-list'))
        self.assertEqual(list_after.data['unread_count'], 0)

    def test_cancel_expired_pending_orders_task(self):
        with schema_context(self.tenant.schema_name):
            hold_showtime_seats(
                owner_id=f'user:{self.user.id}',
                showtime_id=self.showtime.id,
                showtime_seat_ids=[self.ss_1.id],
            )
            expired_order = checkout_cart_to_order(customer=self.customer)
            Order.objects.filter(id=expired_order.id).update(
                created_at=timezone.now() - timedelta(minutes=20)
            )
            expired_tx = Transaction.objects.create(
                order=expired_order,
                amount=expired_order.final_amount,
                status='PENDING',
                authority='S_EXPIRED_001',
            )

            hold_showtime_seats(
                owner_id=f'user:{self.user.id}',
                showtime_id=self.showtime.id,
                showtime_seat_ids=[self.ss_2.id],
            )
            fresh_order = checkout_cart_to_order(customer=self.customer)

        result = cancel_expired_pending_orders(expiration_minutes=15)
        self.assertEqual(result['cancelled_orders'], 1)

        with schema_context(self.tenant.schema_name):
            expired_order.refresh_from_db()
            expired_tx.refresh_from_db()
            self.ss_1.refresh_from_db()
            fresh_order.refresh_from_db()
            self.ss_2.refresh_from_db()

            self.assertEqual(expired_order.status, 'CANCELLED')
            self.assertEqual(expired_tx.status, 'FAILED')
            self.assertEqual(self.ss_1.status, 'AVAILABLE')
            self.assertEqual(Ticket.objects.filter(order=expired_order).count(), 0)

            self.assertEqual(fresh_order.status, 'PENDING')
            self.assertEqual(self.ss_2.status, 'RESERVED')