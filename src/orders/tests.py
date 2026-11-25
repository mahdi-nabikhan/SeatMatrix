from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import threading

from django.contrib.auth import get_user_model
from django.db import connection, connections
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from django_redis import get_redis_connection
from django_tenants.utils import schema_context
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from cinemas.models import Cinema, CinemaDomain, Movie
from operations.models import Address, CinemaBranch, Hall, Seat, Showtime, ShowtimeSeat
from orders.models import Order, Ticket
from orders.redis_locks import cart_key, release_cart, seat_lock_key
from orders.services import checkout_cart_to_order, hold_showtime_seats
from profiles.models import Customer

User = get_user_model()


class OrderConcurrencyAndFlowTests(TransactionTestCase):
    def setUp(self):
        connection.set_schema_to_public()


        self.tenant = Cinema.objects.create(
            schema_name='test_cinema',
            name='Test Cinema',
        )
        self.domain = CinemaDomain.objects.create(
            domain='testcinema.lvh.me',
            tenant=self.tenant,
            is_primary=True,
        )


        self.user = User.objects.create_user(
            username='test_customer',
            email='test_customer@example.com',
            password='StrongPassword123!',
        )
        self.customer = Customer.objects.create(
            user=self.user,
            firstname='Mahdi',
            last_name='Test',
        )
        self.movie = Movie.objects.create(
            title='Inception',
            description='Sci-fi thriller',
            duration_minutes=148,
        )

        connection.set_tenant(self.tenant)

        self.address = Address.objects.create(
            province='Tehran',
            city='Tehran',
            full_address='Valiasr St',
        )
        self.branch = CinemaBranch.objects.create(
            address=self.address,
            branch_name='Cinema Azadi',
        )
        self.hall = Hall.objects.create(
            branch=self.branch,
            name='Hall 1',
            capacity=50,
        )
        self.seat_1 = Seat.objects.create(hall=self.hall, row_label='A', seat_number=1)
        self.seat_2 = Seat.objects.create(hall=self.hall, row_label='A', seat_number=2)

        self.showtime = Showtime.objects.create(
            hall=self.hall,
            movie=self.movie,
            start_time=timezone.now() + timedelta(hours=3),
            base_price=150000,
        )

        self.ss_1, _ = ShowtimeSeat.objects.get_or_create(showtime=self.showtime, seat=self.seat_1)
        self.ss_2, _ = ShowtimeSeat.objects.get_or_create(showtime=self.showtime, seat=self.seat_2)

        self._owners_to_clean = [f'user:{self.user.id}']

    def tearDown(self):

        connection.set_tenant(self.tenant)
        redis_conn = get_redis_connection('default')
        for owner in self._owners_to_clean:
            release_cart(owner)
            redis_conn.delete(cart_key(owner))
        for ss in (self.ss_1, self.ss_2):
            redis_conn.delete(seat_lock_key(self.showtime.id, ss.id))

        connection.set_schema_to_public()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{self.tenant.schema_name}" CASCADE')

    def test_full_guest_to_checkout_flow(self):
        guest_client = APIClient(HTTP_HOST=self.domain.domain)
        other_guest = APIClient(HTTP_HOST=self.domain.domain)

     
        hold_res = guest_client.post(
            reverse('order-cart'),
            {'showtime_id': self.showtime.id, 'showtime_seat_ids': [self.ss_1.id]},
            format='json',
        )
        self.assertEqual(hold_res.status_code, status.HTTP_200_OK)
        guest_token = hold_res.data['guest_token']
        self._owners_to_clean.append(f'guest:{guest_token}')

      
        conflict_res = other_guest.post(
            reverse('order-cart'),
            {'showtime_id': self.showtime.id, 'showtime_seat_ids': [self.ss_1.id, self.ss_2.id]},
            format='json',
            HTTP_X_GUEST_TOKEN='other-guest-token',
        )
        self.assertEqual(conflict_res.status_code, status.HTTP_400_BAD_REQUEST)

        map_url = reverse('showtime-live-seats', kwargs={'showtime_id': self.showtime.id})
        map_guest_1 = guest_client.get(map_url, HTTP_X_GUEST_TOKEN=guest_token).data['seats']
        map_guest_2 = other_guest.get(map_url, HTTP_X_GUEST_TOKEN='other-guest-token').data['seats']

        self.assertEqual(map_guest_1[0]['status'], 'RESERVED_BY_ME')
        self.assertEqual(map_guest_1[1]['status'], 'AVAILABLE')
        self.assertEqual(map_guest_2[0]['status'], 'RESERVED')

        guest_client.force_authenticate(user=self.user)
        claim_res = guest_client.post(
            reverse('order-cart-claim'),
            HTTP_X_GUEST_TOKEN=guest_token,
        )
        self.assertEqual(claim_res.status_code, status.HTTP_200_OK)

      
        checkout_res = guest_client.post(reverse('order-checkout'))
        self.assertEqual(checkout_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(checkout_res.data['status'], 'PAID')
        self.assertEqual(len(checkout_res.data['tickets']), 1)

     
        with schema_context(self.tenant.schema_name):
            self.ss_1.refresh_from_db()
            self.assertEqual(self.ss_1.status, 'SOLD')
            self.assertEqual(Order.objects.count(), 1)
            self.assertEqual(Ticket.objects.count(), 1)

        cart_after = guest_client.get(reverse('order-cart')).data['cart']
        self.assertIsNone(cart_after)

    def test_concurrent_seat_hold_race_condition(self):
        """حمله هم‌زمان ۲۰ کاربر به یک صندلی واحد"""
        num_threads = 20
        barrier = threading.Barrier(num_threads)
        results = {'success': 0, 'failed': 0}
        lock = threading.Lock()
        schema_name = self.tenant.schema_name

        def attempt_hold(idx: int):
            owner_id = f'guest:race-{idx}'
            self._owners_to_clean.append(owner_id)
            try:
                barrier.wait()
                with schema_context(schema_name):
                    hold_showtime_seats(
                        owner_id=owner_id,
                        showtime_id=self.showtime.id,
                        showtime_seat_ids=[self.ss_1.id],
                    )
                with lock:
                    results['success'] += 1
            except ValidationError:
                with lock:
                    results['failed'] += 1
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            list(executor.map(attempt_hold, range(num_threads)))

        self.assertEqual(results['success'], 1)
        self.assertEqual(results['failed'], num_threads - 1)

    def test_concurrent_double_checkout_protection(self):
        """ارسال ۱۰ درخواست هم‌زمان Checkout توسط یک کاربر (جلوگیری از ثبت سفارش تکراری)"""
        owner_id = f'user:{self.user.id}'
        schema_name = self.tenant.schema_name

        with schema_context(schema_name):
            hold_showtime_seats(
                owner_id=owner_id,
                showtime_id=self.showtime.id,
                showtime_seat_ids=[self.ss_1.id],
            )

        num_threads = 10
        barrier = threading.Barrier(num_threads)
        results = {'success': 0, 'failed': 0}
        lock = threading.Lock()

        def attempt_checkout(_):
            try:
                barrier.wait()
                with schema_context(schema_name):
                    checkout_cart_to_order(customer=self.customer)
                with lock:
                    results['success'] += 1
            except ValidationError:
                with lock:
                    results['failed'] += 1
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            list(executor.map(attempt_checkout, range(num_threads)))

        self.assertEqual(results['success'], 1)
        self.assertEqual(results['failed'], num_threads - 1)
        with schema_context(schema_name):
            self.assertEqual(Order.objects.count(), 1)
            self.assertEqual(Ticket.objects.count(), 1)