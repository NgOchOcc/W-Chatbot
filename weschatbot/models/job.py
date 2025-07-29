from sqlalchemy import Column, Integer

from weschatbot.models.base import Base


class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True)