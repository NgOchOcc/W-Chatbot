from typing import List

from sqlalchemy import Integer, Column, String, ForeignKey
from sqlalchemy.orm import mapped_column, relationship, Mapped

from weschatbot.models.base import basic_fields, Base
from weschatbot.utils.db import provide_session


@basic_fields
class User(Base):
    __tablename__ = "users"

    id = mapped_column(Integer, autoincrement=True, primary_key=True, nullable=False)
    name = Column(String(31), nullable=False)
    password = Column(String(2047), nullable=False)
    salt = Column(String(7), nullable=False)

    status: Mapped["UserStatus"] = relationship(back_populates="users")  # noqa
    status_id = Column(Integer, ForeignKey('user_statuses.id'), nullable=False)

    role: Mapped["Role"] = relationship(back_populates="users")
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)

    def __repr__(self):
        return "user:{self.name}".format(self=self)

    @provide_session
    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.name,
            "role": self.role.name,
        }


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(31), nullable=False, unique=True)

    users: Mapped[List["User"]] = relationship(back_populates="role")

    def __repr__(self):
        return "role:{self.name}".format(self=self)

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
        }


@basic_fields
class UserStatus(Base):
    __tablename__ = "user_statuses"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(31), nullable=False, unique=True)

    users: Mapped[List["User"]] = relationship(back_populates="status")

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name
        }

    def __repr__(self):
        return self.name
