import contextlib
from functools import wraps

from weschatbot.utils import setting


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


