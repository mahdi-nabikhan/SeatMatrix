import pytest

from profiles.models import Customer, Manager, Staff


@pytest.mark.django_db
def test_profile_models_creation_and_str(create_user, public_tenant):
    cinema, _ = public_tenant

    manager_user = create_user(
        username='mgr1',
        email='mgr1@example.com',
        phone_number='+989120000011',
    )
    manager = Manager.objects.create(user=manager_user, bank_iban='IR0629600000001003242000')
    assert 'mgr1' in str(manager)

    staff_user = create_user(
        username='stf1',
        email='stf1@example.com',
        phone_number='+989120000012',
    )
    staff = Staff.objects.create(user=staff_user, cinema=cinema, shift='EVENING')
    assert staff.is_active is True
    assert str(staff) == f'Staff: stf1 - {cinema.name}'

    customer_user = create_user(
        username='cust1',
        email='cust1@example.com',
        phone_number='+989120000013',
    )
    customer = Customer.objects.create(
        user=customer_user,
        firstname='Ali',
        last_name='Rezaei',
        age='25',
    )
    assert customer.loyalty_points == 0
    assert str(customer) == 'Customer: cust1'