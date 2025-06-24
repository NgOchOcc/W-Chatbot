import redis

from weschatbot.utils.config import config

DB_CHAT = 1


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
