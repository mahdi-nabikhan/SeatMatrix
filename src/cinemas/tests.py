from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinemas.cache import invalidate_movie_caches
from cinemas.models import Cinema, CinemaDomain, Movie
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django_tenants.utils import schema_context

from operations.models import Address, CinemaBranch, Hall, Seat, Showtime, ShowtimeSeat
from orders.models import Order, Ticket
from profiles.models import Customer

User = get_user_model()


class MovieCacheTests(TransactionTestCase):
    def setUp(self):
        connection.set_schema_to_public()
        invalidate_movie_caches()

        self.tenant = Cinema.objects.create(
            schema_name='test_cinema_cache',
            name='Test Cinema Cache',
        )
        self.domain = CinemaDomain.objects.create(
            domain='cachetest.lvh.me',
            tenant=self.tenant,
            is_primary=True,
        )
        self.movie = Movie.objects.create(
            title='Inception',
            description='Dream heist',
            duration_minutes=148,
            created_by_cinema=self.tenant,
        )
        self.client = APIClient(HTTP_HOST=self.domain.domain)

    def tearDown(self):
        connection.set_schema_to_public()
        invalidate_movie_caches(movie_id=self.movie.id)
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{self.tenant.schema_name}" CASCADE')

    def test_movie_list_cache_hit_and_invalidation(self):
        url = reverse('cinemas:movie-list')

        with CaptureQueriesContext(connection) as miss_queries:
            res1 = self.client.get(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1['X-Cache'], 'MISS')

        with CaptureQueriesContext(connection) as hit_queries:
            res2 = self.client.get(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2['X-Cache'], 'HIT')
        self.assertLess(len(hit_queries), len(miss_queries))

        connection.set_schema_to_public()
        self.movie.title = 'Inception Updated'
        self.movie.save()

        res3 = self.client.get(url)
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(res3['X-Cache'], 'MISS')

        items = res3.data['results'] if isinstance(res3.data, dict) and 'results' in res3.data else res3.data
        self.assertEqual(items[0]['title'], 'Inception Updated')

    def test_movie_detail_cache_hit_and_invalidation(self):
        url = reverse('cinemas:movie-detail', kwargs={'pk': self.movie.id})

        res1 = self.client.get(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1['X-Cache'], 'MISS')

        res2 = self.client.get(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2['X-Cache'], 'HIT')

        connection.set_schema_to_public()
        self.movie.duration_minutes = 150
        self.movie.save()

        res3 = self.client.get(url)
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(res3['X-Cache'], 'MISS')
        self.assertEqual(res3.data['duration_minutes'], 150)
        
        
    
    


class MovieRecommendationTests(TransactionTestCase):
    def setUp(self):
        connection.set_schema_to_public()
        cache.clear()

        self.tenant = Cinema.objects.create(
            schema_name='test_cinema_rec',
            name='Test Cinema Rec',
        )
        self.domain = CinemaDomain.objects.create(
            domain='rectest.lvh.me',
            tenant=self.tenant,
            is_primary=True,
        )

        self.user_1 = User.objects.create_user(
            username='rec_user_1',
            email='rec1@example.com',
            password='StrongPassword123!',
        )
        self.customer_1 = Customer.objects.create(
            user=self.user_1,
            firstname='Ali',
            last_name='One',
        )
        self.user_2 = User.objects.create_user(
            username='rec_user_2',
            email='rec2@example.com',
            password='StrongPassword123!',
        )
        self.customer_2 = Customer.objects.create(
            user=self.user_2,
            firstname='Sara',
            last_name='Two',
        )

        self.movie_scifi_1 = Movie.objects.create(
            title='Interstellar',
            description='Space travel',
            genre=Movie.GenreChoices.SCI_FI,
            duration_minutes=169,
        )
        self.movie_scifi_2 = Movie.objects.create(
            title='Blade Runner 2049',
            description='Cyberpunk future',
            genre=Movie.GenreChoices.SCI_FI,
            duration_minutes=164,
        )
        self.movie_comedy = Movie.objects.create(
            title='The Hangover',
            description='Comedy trip',
            genre=Movie.GenreChoices.COMEDY,
            duration_minutes=100,
        )

        with schema_context(self.tenant.schema_name):
            address = Address.objects.create(
                province='Tehran',
                city='Tehran',
                full_address='Valiasr St',
            )
            branch = CinemaBranch.objects.create(address=address, branch_name='Main Branch')
            hall = Hall.objects.create(branch=branch, name='Hall 1', capacity=20)
            seat_1 = Seat.objects.create(hall=hall, row_label='A', seat_number=1)
            seat_2 = Seat.objects.create(hall=hall, row_label='A', seat_number=2)

            st_1 = Showtime.objects.create(
                hall=hall,
                movie=self.movie_scifi_1,
                start_time=timezone.now() + timedelta(hours=3),
                base_price=150000,
            )
            st_2 = Showtime.objects.create(
                hall=hall,
                movie=self.movie_scifi_2,
                start_time=timezone.now() + timedelta(hours=5),
                base_price=150000,
            )
            ss_1_a, _ = ShowtimeSeat.objects.get_or_create(showtime=st_1, seat=seat_1)
            ss_1_b, _ = ShowtimeSeat.objects.get_or_create(showtime=st_1, seat=seat_2)
            ss_2_a, _ = ShowtimeSeat.objects.get_or_create(showtime=st_2, seat=seat_1)

            order_1 = Order.objects.create(
                customer=self.customer_1,
                order_number='ORD-REC-001',
                status='PAID',
                total_amount=150000,
                discount_amount=0,
                final_amount=150000,
            )
            Ticket.objects.create(order=order_1, showtime_seat=ss_1_a, price=150000)

            order_2 = Order.objects.create(
                customer=self.customer_2,
                order_number='ORD-REC-002',
                status='PAID',
                total_amount=300000,
                discount_amount=0,
                final_amount=300000,
            )
            Ticket.objects.create(order=order_2, showtime_seat=ss_1_b, price=150000)
            Ticket.objects.create(order=order_2, showtime_seat=ss_2_a, price=150000)

        self.client = APIClient(HTTP_HOST=self.domain.domain)

    def tearDown(self):
        connection.set_schema_to_public()
        cache.clear()
        with connection.cursor() as cursor:
            cursor.execute(f'DROP SCHEMA IF EXISTS "{self.tenant.schema_name}" CASCADE')

    def test_anonymous_user_gets_trending_recommendations_with_cache(self):
        url = reverse('cinemas:movie-recommended')

        res1 = self.client.get(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['strategy'], 'trending')
        self.assertEqual(res1['X-Cache'], 'MISS')
        self.assertEqual(res1.data['results'][0]['id'], self.movie_scifi_1.id)

        res2 = self.client.get(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2['X-Cache'], 'HIT')

    def test_authenticated_user_gets_personalized_hybrid_recommendations(self):
        self.client.force_authenticate(user=self.user_1)
        url = reverse('cinemas:movie-recommended')

        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['strategy'], 'personalized')

        returned_ids = [item['id'] for item in res.data['results']]
        self.assertNotIn(self.movie_scifi_1.id, returned_ids)
        self.assertEqual(returned_ids[0], self.movie_scifi_2.id)
        self.assertGreater(
            res.data['results'][0]['recommendation_score'],
            res.data['results'][1]['recommendation_score'],
        )