from sqlalchemy import create_engine, QueuePool
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from weschatbot.utils.config import config

mysql_config = config["db"]
mysql_engine = None
mysql_session = None

async_engine = None
mysql_async_session = None


def configure_async_sqlalchemy_session():
    global mysql_async_session
    global async_engine

    async_engine = create_async_engine(mysql_config["async_sql_alchemy_conn"], echo=True)
    mysql_async_session = async_sessionmaker(
        autoflush=True,
        expire_on_commit=False,
        bind=async_engine,
        class_=AsyncSession
    )


def configure_sqlalchemy_session():
    global mysql_session
    global mysql_config
    global mysql_engine

    mysql_engine = create_engine(
        mysql_config["sql_alchemy_conn"],
        poolclass=QueuePool,
        pool_size=10,
        pool_recycle=28000,
        echo=False)

    mysql_session = scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=True,
            bind=mysql_engine,
            expire_on_commit=False
        )
    )


def initialize():
    configure_sqlalchemy_session()
    configure_async_sqlalchemy_session()


initialize()
