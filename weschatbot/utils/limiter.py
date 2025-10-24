import time

from pyrate_limiter import Rate, RateItem
from pyrate_limiter import RedisBucket
from redis.asyncio import Redis

from weschatbot.utils.config import config


def limiter(user_id, interval, limit, failing_callback):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            redis_client = Redis(host=config["redis"]["host"], port=int(config["redis"]["port"]), db=0,
                                 decode_responses=True)

            rates = [Rate(interval=interval, limit=limit)]
            bucket = await RedisBucket.init(rates, redis_client, f"bucket:limiter_{func.__name__}_{user_id}")
            item = RateItem(name="call", timestamp=int(time.time()), weight=1)
            ok = await bucket.put(item)
            if not ok:
                # failing = bucket.failing_rate
                print("Reached limit")
                await failing_callback()
            else:
                return await func(*args, **kwargs)

        return wrapper

    return decorator
