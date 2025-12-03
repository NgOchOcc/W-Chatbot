import logging
import time

from pyrate_limiter import Rate, RateItem
from pyrate_limiter import RedisBucket
from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from weschatbot.utils.config import config

logger = logging.getLogger(__name__)

_redis_client = None
_pool = ConnectionPool(host=config.get("redis", "host"), port=config.getint("redis", "port"), db=0, max_connections=10)


def get_redis_client(database: int):
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis(host=config["redis"]["host"], port=int(config["redis"]["port"]), db=0,
                              decode_responses=True, pool=_pool)
    return _redis_client


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
                logger.info("Reached limit")
                await failing_callback()
            else:
                return await func(*args, **kwargs)

        return wrapper

    return decorator
