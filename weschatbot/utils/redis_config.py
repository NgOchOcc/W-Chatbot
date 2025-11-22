import functools
import inspect
import pickle

import redis

from weschatbot.utils.config import config

DB_CHAT = 1
DB_CACHE = 2


def create_redis_client(database):
    return redis.Redis(host=config["redis"]["host"], port=int(config["redis"]["port"]), db=database)


redis_client = lambda database: create_redis_client(database)


def provide_redis(database):
    arg_redis = "redis_client"

    def decorator(func):
        def wrapper(*args, **kwargs):
            func_params = func.__code__.co_varnames
            session_in_args = arg_redis in func_params and func_params.index(arg_redis) < len(args)
            session_in_kwargs = arg_redis in kwargs

            if session_in_kwargs or session_in_args:
                return func(*args, **kwargs)
            else:
                r = redis_client(database)
                kwargs[arg_redis] = r
                return func(*args, **kwargs)

        return wrapper

    return decorator


def redis_cache(expire_seconds=3600, key_args=None, db=DB_CACHE):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            r = create_redis_client(database=db)

            sig = inspect.signature(fn)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            arg_map = bound.arguments

            key_parts = [fn.__name__]
            if key_args:
                for k in key_args:
                    val = arg_map.get(k)
                    key_parts.append(f"{k}={val}")
            redis_key = "cache:" + "|".join(key_parts)

            cached = r.get(redis_key)
            if cached:
                return pickle.loads(cached)

            result = fn(*args, **kwargs)
            r.setex(redis_key, expire_seconds, pickle.dumps(result))
            return result

        return wrapper

    return decorator
