import functools
import inspect
import logging
import pickle
import threading
from typing import Dict, Callable, Optional, Iterable

import redis

from weschatbot.utils.config import config

DB_CHAT = 1
DB_CACHE = 2

logger = logging.getLogger(__name__)

_redis_clients: Dict[int, redis.Redis] = {}
_clients_lock = threading.Lock()


def create_redis_client(database: int) -> redis.Redis:
    return redis.Redis(
        host=config["redis"]["host"],
        port=int(config["redis"]["port"]),
        db=database,
        decode_responses=False,
        socket_keepalive=True,
    )


def get_redis_client(database: int) -> redis.Redis:
    with _clients_lock:
        client = _redis_clients.get(database)
        if client is None:
            client = create_redis_client(database)
            _redis_clients[database] = client
        return client


def close_all_redis_clients() -> None:
    with _clients_lock:
        for db, client in list(_redis_clients.items()):
            try:
                client.close()
                try:
                    client.connection_pool.disconnect()
                except Exception as e:
                    logger.warning("Failed to close redis client for db=%s: %s", db, e)
                    pass
                logger.info("Closed redis client for db=%s", db)
            except Exception as e:
                logger.exception("Error closing redis client for db=%s: %s", db, e)
        _redis_clients.clear()


def redis_client(database: int) -> redis.Redis:
    return get_redis_client(database)


def provide_redis(database: int):
    arg_name = "redis_client"

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_params = func.__code__.co_varnames
            session_in_args = arg_name in func_params and func_params.index(arg_name) < len(args)
            session_in_kwargs = arg_name in kwargs

            if session_in_args or session_in_kwargs:
                return func(*args, **kwargs)

            r = get_redis_client(database)
            kwargs[arg_name] = r
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _build_cache_key(fn: Callable, key_args: Optional[Iterable[str]], bound_args: inspect.BoundArguments) -> str:
    key_parts = [fn.__name__]
    if key_args:
        for k in key_args:
            val = bound_args.arguments.get(k)
            key_parts.append(f"{k}={repr(val)}")
    else:
        for name, val in bound_args.arguments.items():
            key_parts.append(f"{name}={repr(val)}")
    return "cache:" + "|".join(key_parts)


def redis_cache(expire_seconds: int = 3600, key_args: Optional[Iterable[str]] = None, db: int = DB_CACHE):
    def decorator(fn: Callable):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            r = get_redis_client(db)

            sig = inspect.signature(fn)
            try:
                bound = sig.bind(*args, **kwargs)
            except TypeError:
                bound = None

            if bound is not None:
                bound.apply_defaults()
                redis_key = _build_cache_key(fn, key_args, bound)
            else:
                redis_key = f"cache:{fn.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            try:
                cached = r.get(redis_key)
            except Exception as e:
                logger.exception("Redis GET error for key=%s: %s", redis_key, e)
                cached = None

            if cached:
                try:
                    return pickle.loads(cached)
                except Exception as e:
                    logger.exception("Failed to unpickle cached value for key=%s: %s", redis_key, e)

            result = fn(*args, **kwargs)

            try:
                pickled = pickle.dumps(result)
                r.setex(redis_key, expire_seconds, pickled)
            except Exception as e:
                logger.exception("Redis SETEX error for key=%s: %s", redis_key, e)

            return result

        return wrapper

    return decorator
