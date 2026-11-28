import logging
import urllib.error

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from cinemas.cache import invalidate_movie_caches
from cinemas.models import Movie, MovieImage
from cinemas.search import delete_movie_from_index, index_movie

logger = logging.getLogger(__name__)


def _safe_index_movie(movie: Movie) -> None:
    """Best-effort Elasticsearch upsert that logs failures without breaking DB writes."""
    try:
        index_movie(movie)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning('Failed to sync movie %s to Elasticsearch: %s', movie.pk, exc)


def _safe_delete_movie(movie_id: int) -> None:
    """Best-effort Elasticsearch delete that logs failures without breaking DB deletes."""
    try:
        delete_movie_from_index(movie_id)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning('Failed to delete movie %s from Elasticsearch: %s', movie_id, exc)


@receiver(post_save, sender=Movie)
def sync_on_movie_save(sender, instance, **kwargs):
    """Invalidate movie caches and sync the saved Movie document to Elasticsearch on commit."""
    movie_id = instance.pk
    transaction.on_commit(lambda: invalidate_movie_caches(movie_id=movie_id))
    transaction.on_commit(lambda: _safe_index_movie(instance))


@receiver(post_delete, sender=Movie)
def sync_on_movie_delete(sender, instance, **kwargs):
    """Invalidate movie caches and remove the deleted Movie from Elasticsearch on commit."""
    movie_id = instance.pk
    transaction.on_commit(lambda: invalidate_movie_caches(movie_id=movie_id))
    transaction.on_commit(lambda: _safe_delete_movie(movie_id))


@receiver([post_save, post_delete], sender=MovieImage)
def invalidate_on_movie_image_change(sender, instance, **kwargs):
    """Invalidate cached list and detail entries when a movie's gallery image changes."""
    movie_id = instance.movie_id
    transaction.on_commit(lambda: invalidate_movie_caches(movie_id=movie_id))