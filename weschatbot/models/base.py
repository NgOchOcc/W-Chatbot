from sqlalchemy import TIMESTAMP, Column, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def basic_fields(cls):
    cls.modified_date = Column(TIMESTAMP, nullable=False, default=func.now())

    return cls
