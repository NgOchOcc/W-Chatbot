from typing import List

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, relationship

from weschatbot.models.base import Base, basic_fields
from weschatbot.utils.db import provide_session


@basic_fields
class Job(Base):
    __tablename__ = 'jobs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(63), nullable=False)
    class_name = Column(String(511), nullable=False)
    params = Column(String(511), nullable=True)

    status: Mapped["JobStatus"] = relationship(back_populates="jobs")
    status_id = Column(Integer, ForeignKey("job_statuses.id"), nullable=False)

    @provide_session
    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "params": self.params,
            "class_name": self.class_name,
            "status": self.status.name,
        }


class JobStatus(Base):
    __tablename__ = 'job_statuses'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(31), nullable=False, unique=True)

    jobs: Mapped[List["Job"]] = relationship(back_populates="status")

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
        }

    def __repr__(self):
        return self.name
