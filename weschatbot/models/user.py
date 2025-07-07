import json
from typing import List

from flask_login import UserMixin
from sqlalchemy import Integer, Column, String, ForeignKey, Table, Boolean
from sqlalchemy.orm import mapped_column, relationship, Mapped

from weschatbot.models.base import basic_fields, Base
from weschatbot.utils.db import provide_session


@basic_fields
class User(Base, UserMixin):
    __tablename__ = "users"

    id = mapped_column(Integer, autoincrement=True, primary_key=True, nullable=False)
    name = Column(String(31), nullable=False)
    password = Column(String(2047), nullable=False)
    salt = Column(String(7), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    role: Mapped["Role"] = relationship(back_populates="users")
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)

    chats: Mapped[List["ChatSession"]] = relationship(back_populates="user")

    def __repr__(self):
        return "user:{self.name}".format(self=self)

    @provide_session
    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.to_dict(session=session),
            "is_active": self.is_active,
        }

    @provide_session
    def to_json(self, session=None):
        return json.dumps(self.to_dict(session=session))

    def get_id(self):
        return self.id


role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True)
)


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, autoincrement=True, primary_key=True, nullable=False)
    name = Column(String(31), nullable=False)

    roles: Mapped[List["Role"]] = relationship(
        "Role",
        secondary=role_permissions,
        back_populates="permissions"
    )

    def __repr__(self):
        return "{self.name}".format(self=self)

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name
        }


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(31), nullable=False, unique=True)

    users: Mapped[List["User"]] = relationship(back_populates="role")

    permissions: Mapped[List["Permission"]] = relationship(
        "Permission",
        secondary=role_permissions,
        back_populates="roles"
    )

    def __repr__(self):
        return "{self.name}".format(self=self)

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "permissions": [p.to_dict(session=session) for p in self.permissions]
        }


@basic_fields
class ChatStatus(Base):
    __tablename__ = "chat_statuses"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(31), nullable=False, unique=True)

    chats: Mapped[List["ChatSession"]] = relationship(back_populates="status")

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name
        }

    def __repr__(self):
        return self.name


@basic_fields
class ChatSession(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(31), nullable=False, unique=False)

    user: Mapped["User"] = relationship(back_populates="chats")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    messages: Mapped[List["ChatMessage"]] = relationship(back_populates="chat")
    uuid = Column(String(36), nullable=False, unique=True)

    status: Mapped["ChatStatus"] = relationship(back_populates="chats")  # noqa
    status_id = Column(Integer, ForeignKey('chat_statuses.id'), nullable=False)

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "user": self.user and self.user.to_dict(session=session) or {},
            "uuid": self.uuid,
            "modified_date": self.modified_date.strftime("%Y-%m-%d %H:%M:%S"),
            # "messages": [x.to_dict() for x in self.messages],
        }


@basic_fields
class ChatMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(31), nullable=False, unique=False)
    content = Column(String(2047), nullable=False)
    sender = Column(String(4), nullable=False)

    chat: Mapped["ChatSession"] = relationship(back_populates="messages")
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
        }

    def __repr__(self):
        return f"{self.sender}: {self.content}\n"
