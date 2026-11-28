import pytest
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse

from profiles.models import Manager

User = get_user_model()


def promo_url(name: str, **kwargs) -> str:
    """Resolve a promotions URL regardless of whether core/urls.py applies a namespace."""
    for candidate in (name, f'promotions:{name}', f'promotions-v1:{name}'):
        try:
            return reverse(candidate, kwargs=kwargs)
        except NoReverseMatch:
            continue
    raise NoReverseMatch(f'Could not resolve promotions URL: {name}')


@pytest.fixture
def setup_promo_tenant(make_tenant, db):
    """Provision a tenant cinema with an owning Manager and a regular User."""
    def _setup(schema_name='test_promo', cinema_name='Promo Cinema', host='promo.lvh.me'):
        tenant, domain, client = make_tenant(schema_name, cinema_name, host)

        mgr_user = User.objects.create_user(
            username=f'{schema_name}_mgr',
            email=f'{schema_name}_mgr@example.com',
            password='StrongPassword123!',
            phone_number=f'+98916{abs(hash(schema_name)) % 10000000:07d}',
        )
        manager = Manager.objects.create(user=mgr_user, bank_iban='IR1234567890123456789012')
        tenant.manager = manager
        tenant.save(update_fields=['manager'])

        regular_user = User.objects.create_user(
            username=f'{schema_name}_usr',
            email=f'{schema_name}_usr@example.com',
            password='StrongPassword123!',
            phone_number=f'+98917{abs(hash(schema_name)) % 10000000:07d}',
        )

        return {
            'tenant': tenant,
            'domain': domain,
            'client': client,
            'manager_user': mgr_user,
            'regular_user': regular_user,
        }

    return _setup