import json
from django.db import connection
from django_redis import get_redis_connection

HOLD_TTL_SECONDS = 600 

HOLD_SEATS_LUA = """
local owner = ARGV[1]
local ttl = tonumber(ARGV[2])

for i, key in ipairs(KEYS) do
    local current = redis.call('GET', key)
    if current and current ~= owner then
        return 0
    end
end

for i, key in ipairs(KEYS) do
    redis.call('SET', key, owner, 'EX', ttl)
end

return 1
"""

RELEASE_SEATS_LUA = """
local owner = ARGV[1]
for i, key in ipairs(KEYS) do
    if redis.call('GET', key) == owner then
        redis.call('DEL', key)
    end
end
return 1
"""

CLAIM_SEATS_LUA = """
local guest_owner = ARGV[1]
local user_owner = ARGV[2]
local ttl = tonumber(ARGV[3])

for i, key in ipairs(KEYS) do
    if redis.call('GET', key) ~= guest_owner then
        return 0
    end
end

for i, key in ipairs(KEYS) do
    redis.call('SET', key, user_owner, 'EX', ttl)
end

return 1
"""


def _schema_prefix() -> str:
    return getattr(connection, 'schema_name', 'public')


def seat_lock_key(showtime_id: int, seat_id: int) -> str:
    return f"{_schema_prefix()}:seat_lock:{showtime_id}:{seat_id}"


def cart_key(owner_id: str) -> str:
    return f"{_schema_prefix()}:cart:{owner_id}"


def build_owner_id(user, guest_token: str | None) -> str | None:
    if user and user.is_authenticated:
        return f"user:{user.id}"
    if guest_token:
        return f"guest:{guest_token.strip()}"
    return None


def get_cart(owner_id: str) -> dict | None:
    redis_conn = get_redis_connection("default")
    raw = redis_conn.get(cart_key(owner_id))
    return json.loads(raw) if raw else None


def hold_seats_in_redis(*, owner_id: str, showtime_id: int, seat_ids: list[int]) -> bool:
    redis_conn = get_redis_connection("default")
    keys = [seat_lock_key(showtime_id, sid) for sid in seat_ids]

    acquired = redis_conn.eval(
        HOLD_SEATS_LUA,
        len(keys),
        *keys,
        owner_id,
        HOLD_TTL_SECONDS,
    )
    if not acquired:
        return False


    old_cart = get_cart(owner_id)
    if old_cart:
        old_showtime = old_cart['showtime_id']
        old_seats = set(old_cart['seat_ids'])
        new_seats = set(seat_ids) if old_showtime == showtime_id else set()
        leftover_seats = old_seats - new_seats
        if leftover_seats:
            leftover_keys = [seat_lock_key(old_showtime, sid) for sid in leftover_seats]
            redis_conn.eval(RELEASE_SEATS_LUA, len(leftover_keys), *leftover_keys, owner_id)

    payload = {
        "showtime_id": showtime_id,
        "seat_ids": seat_ids,
    }
    redis_conn.set(cart_key(owner_id), json.dumps(payload), ex=HOLD_TTL_SECONDS)
    return True


def release_cart(owner_id: str) -> None:
    redis_conn = get_redis_connection("default")
    cart = get_cart(owner_id)
    if not cart:
        return

    keys = [seat_lock_key(cart['showtime_id'], sid) for sid in cart['seat_ids']]
    if keys:
        redis_conn.eval(RELEASE_SEATS_LUA, len(keys), *keys, owner_id)
    redis_conn.delete(cart_key(owner_id))


def claim_guest_cart(*, guest_token: str, user_id: int) -> dict | None:
    redis_conn = get_redis_connection("default")
    guest_owner = f"guest:{guest_token.strip()}"
    user_owner = f"user:{user_id}"

    cart = get_cart(guest_owner)
    if not cart:
        return None

  
    release_cart(user_owner)

    keys = [seat_lock_key(cart['showtime_id'], sid) for sid in cart['seat_ids']]
    claimed = redis_conn.eval(
        CLAIM_SEATS_LUA,
        len(keys),
        *keys,
        guest_owner,
        user_owner,
        HOLD_TTL_SECONDS,
    )
    if not claimed:
        redis_conn.delete(cart_key(guest_owner))
        return None

    redis_conn.set(cart_key(user_owner), json.dumps(cart), ex=HOLD_TTL_SECONDS)
    redis_conn.delete(cart_key(guest_owner))
    return cart


def get_locked_seats_map(*, showtime_id: int, seat_ids: list[int]) -> dict[int, str]:
    if not seat_ids:
        return {}
    redis_conn = get_redis_connection("default")
    keys = [seat_lock_key(showtime_id, sid) for sid in seat_ids]
    values = redis_conn.mget(keys)
    return {
        sid: (val.decode('utf-8') if isinstance(val, bytes) else val)
        for sid, val in zip(seat_ids, values)
        if val is not None
    }