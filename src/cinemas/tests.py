from django.db import connection
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from cinemas.cache import invalidate_movie_caches
from cinemas.models import Cinema, CinemaDomain, Movie


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