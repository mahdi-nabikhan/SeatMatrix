from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cinemas.cache import invalidate_movie_caches
from cinemas.models import Movie, MovieImage


@receiver([post_save, post_delete], sender=Movie)
def invalidate_on_movie_change(sender, instance, **kwargs):
    movie_id = instance.pk
    transaction.on_commit(lambda: invalidate_movie_caches(movie_id=movie_id))


@receiver([post_save, post_delete], sender=MovieImage)
def invalidate_on_movie_image_change(sender, instance, **kwargs):
    movie_id = instance.movie_id
    transaction.on_commit(lambda: invalidate_movie_caches(movie_id=movie_id))