import pytest
from django.contrib.auth import get_user_model
from django.urls import NoReverseMatch, reverse

from profiles.models import Manager, Staff

User = get_user_model()


def op_url(name: str, **kwargs) -> str:
    """Resolve an operations URL regardless of whether core/urls.py applies a namespace."""
    for candidate in (name, f'operations:{name}', f'operations-v1:{name}'):
        try:
            return reverse(candidate, kwargs=kwargs)
        except NoReverseMatch:
            continue
    raise NoReverseMatch(f'Could not resolve operations URL: {name}')


@pytest.fixture
def create_user(db):
    def _create(username, email, phone_number, password='StrongPassword123!'):
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
            phone_number=phone_number,
        )

    return _create


@pytest.fixture
def setup_cinema_roles(make_tenant, create_user):
    """Provision a tenant cinema with an owning Manager, an active Staff, and a regular User."""
    def _setup(schema_name, cinema_name, host):
        tenant, domain, client = make_tenant(schema_name, cinema_name, host)

        mgr_user = create_user(
            username=f'{schema_name}_mgr',
            email=f'{schema_name}_mgr@example.com',
            phone_number=f'+98912{abs(hash(schema_name)) % 10000000:07d}',
        )
        manager = Manager.objects.create(user=mgr_user, bank_iban='IR1234567890123456789012')
        tenant.manager = manager
        tenant.save(update_fields=['manager'])

        staff_user = create_user(
            username=f'{schema_name}_stf',
            email=f'{schema_name}_stf@example.com',
            phone_number=f'+98913{abs(hash(schema_name)) % 10000000:07d}',
        )
        staff = Staff.objects.create(user=staff_user, cinema=tenant, shift='MORNING', is_active=True)

        regular_user = create_user(
            username=f'{schema_name}_usr',
            email=f'{schema_name}_usr@example.com',
            phone_number=f'+98914{abs(hash(schema_name)) % 10000000:07d}',
        )

        return {
            'tenant': tenant,
            'domain': domain,
            'client': client,
            'manager_user': mgr_user,
            'manager': manager,
            'staff_user': staff_user,
            'staff': staff,
            'regular_user': regular_user,
        }

    return _setup