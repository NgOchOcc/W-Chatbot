import contextlib
import redis
from functools import wraps

from weschatbot.utils import setting
from weschatbot.utils.config import config


@contextlib.contextmanager
def create_session():
    session = setting.mysql_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def provide_session(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        arg_session = 'session'

        func_params = func.__code__.co_varnames
        session_in_args = arg_session in func_params and func_params.index(arg_session) < len(args)
        session_in_kwargs = arg_session in kwargs

        if session_in_kwargs or session_in_args:
            return func(*args, **kwargs)
        else:
            with create_session() as session:
                kwargs[arg_session] = session
                return func(*args, **kwargs)

    return wrapper


@contextlib.asynccontextmanager
async def create_async_session():
    session = setting.mysql_async_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def provide_async_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        arg_session = 'async_session'

        func_params = func.__code__.co_varnames
        session_in_args = arg_session in func_params and func_params.index(arg_session) < len(args)
        session_in_kwargs = arg_session in kwargs

        if session_in_kwargs or session_in_args:
            return await func(*args, **kwargs)
        else:
            async with create_async_session() as session:
                kwargs[arg_session] = session
                return await func(*args, **kwargs)

    return wrapper


def create_redis_client():
    def wrapper(database):
        return redis.Redis(host=config["redis"]["host"], port=int(config["redis"]["port"]), db=database)

    return wrapper


redis_client = lambda database: create_redis_client()


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
