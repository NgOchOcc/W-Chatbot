import asyncio
import datetime
import functools

SCAN_COUNT = 1000


class ActiveUser:
    def __init__(self, user_id, last_active):
        self.user_id = user_id
        self.last_active = last_active

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'last_active': self.last_active
        }


class ActiveStatusService:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.presence_key = "presence:{user_id}"

    def active(self, user_id, ttl_seconds=600):
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if user_id is None:
                    try:
                        return await func(*args, **kwargs)
                    except Exception:
                        raise

                key = self.presence_key.format(user_id=user_id)
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.redis_client.setex(key, ttl_seconds, datetime.datetime.now().timestamp()),
                )  # noqa

                try:
                    return await func(*args, **kwargs)
                except Exception:
                    raise

            return wrapper

        return decorator

    def presence_pattern(self):
        return self.presence_key.replace("{user_id}", "*")

    @staticmethod
    def extract_user_id_from_key(key):
        return key.split(":")[1]

    def get_all_active_user(self):
        pattern = self.presence_pattern()
        cursor = 0
        users = []
        while True:
            cursor, keys = self.redis_client.scan(cursor=cursor, match=pattern, count=SCAN_COUNT)
            if keys:
                users.extend(keys)
            if cursor == 0:
                break

        result = []
        if not users:
            return result

        batch_size = SCAN_COUNT
        for i in range(0, len(users), batch_size):
            batch_keys = users[i: i + batch_size]
            values = self.redis_client.mget(batch_keys)
            for key, val in zip(batch_keys, values):
                if val is None:
                    continue
                try:
                    ts = float(val)
                    dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
                except Exception:
                    try:
                        dt = datetime.datetime.fromisoformat(val)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=datetime.timezone.utc)
                    except Exception:
                        dt = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
                user_id = self.extract_user_id_from_key(key.decode())
                result.append(ActiveUser(user_id, dt))

        return result
