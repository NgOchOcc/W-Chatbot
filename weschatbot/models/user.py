import json
from typing import List

from flask_login import UserMixin
from sqlalchemy import Integer, Column, String, ForeignKey, Table, Boolean, Text, Float, BigInteger, Index, \
    DateTime
from sqlalchemy.orm import mapped_column, relationship, Mapped

from weschatbot.models.base import basic_fields, Base
from weschatbot.utils.db import provide_session


@basic_fields
class User(Base, UserMixin):
    __tablename__ = "users"

    id = mapped_column(Integer, autoincrement=True, primary_key=True, nullable=False)
    name = Column(String(31), nullable=False)
    password = Column(String(2047), nullable=False)
    salt = Column(String(7), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    role: Mapped["Role"] = relationship(back_populates="users")
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)

    chats: Mapped[List["ChatSession"]] = relationship(back_populates="user")

    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return "user:{self.name}".format(self=self)

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


@basic_fields
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, nullable=False)
    token = Column(String(2047), nullable=False)

    user_agent_raw = Column(String(1024), nullable=True)

    ip_address = Column(String(64), nullable=True)
    accept_language = Column(String(128), nullable=True)

    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked = Column(Boolean, nullable=False, default=False, index=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
                                         index=True)
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_user_expires", "user_id", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} user_id={self.user_id} revoked={self.revoked}>"

    name = str(token)

    @provide_session
    def to_dict(self, session=None):
        data = {
            "id": self.id,
            "token": self.token,
            "user_agent_raw": self.user_agent_raw,
            "ip_address": self.ip_address,
            "accept_language": self.accept_language,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "revoked": self.revoked,
            "user_id": self.user_id,
            "user_name": self.user.name if self.user else None,
        }
        return data


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
            "name": self.name
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
            "modified_date": self.modified_date.strftime("%Y-%m-%d %H:%M:%S"),  # noqa
            "messages": [x.to_dict() for x in self.messages],
            "status": self.status.name,
        }


@basic_fields
class ChatMessage(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(31), nullable=False, unique=False)
    content = Column(Text, nullable=False)
    sender = Column(String(4), nullable=False)

    chat: Mapped["ChatSession"] = relationship(back_populates="messages")
    chat_id = Column(Integer, ForeignKey('chats.id'), nullable=False)

    queries: Mapped[List["Query"]] = relationship(back_populates="message")

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "sender": self.sender,
            "modified_date": self.modified_date.isoformat(),  # noqa
        }

    def __repr__(self):
        return f"{self.sender}: {self.content}\n"


@basic_fields
class Query(Base):
    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    document: Mapped["Document"] = relationship(back_populates="queries")

    row_id = Column(BigInteger, nullable=False)
    document_text = Column(Text, nullable=False)
    cosine_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)

    message: Mapped["ChatMessage"] = relationship(back_populates="queries")

    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False)
    collection: Mapped["Collection"] = relationship(back_populates="queries")

    def to_dict(self):
        return {
            "id": self.id,
            "message_id": self.message_id,
            "document_id": self.document_id,
            "row_id": self.row_id,
            "document_text": self.document_text,
            "cosine_score": self.cosine_score,
            "collection_id": self.collection_id,
            "collection_name": self.collection.name if self.collection else None,
            "document_name": self.document.name if self.document else None,
            "rank": self.rank,
            "message_content": self.message.content if self.message else None
        }


@basic_fields
class Collection(Base):
    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(63), nullable=False)

    status_id = Column(Integer, ForeignKey("collection_statuses.id"), nullable=False)
    status: Mapped["CollectionStatus"] = relationship(back_populates="collections")

    documents_link: Mapped[List["CollectionDocument"]] = relationship(back_populates="collection")

    queries: Mapped[List["Query"]] = relationship(back_populates="collection")

    chatbot_configurations: Mapped[List["ChatbotConfiguration"]] = relationship(
        "ChatbotConfiguration",
        back_populates="collection"
    )

    def __repr__(self):
        return self.name

    @provide_session
    def to_dict(self, session=None):
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status.name
        }


@basic_fields
class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(255), nullable=False)
    path = Column(String(2047), nullable=False)
    converted_path = Column(String(2047), nullable=True)
    is_used = Column(Boolean, nullable=False, default=False)
    status_id = Column(Integer, ForeignKey('document_statuses.id'), nullable=False)
    status: Mapped["DocumentStatus"] = relationship(back_populates="documents")

    collections_link: Mapped[List["CollectionDocument"]] = relationship(back_populates="document")

    queries: Mapped[List["Query"]] = relationship(back_populates="document")  # noqa

    @provide_session
    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "is_used": self.is_used,
            "status": self.status.name,
            "converted_path": self.converted_path,
        }


class DocumentStatus(Base):
    __tablename__ = "document_statuses"

    id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    name = Column(String(255), nullable=False, unique=False)

    documents: Mapped[List["Document"]] = relationship(back_populates="status")

    @provide_session
    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
        }

    def __repr__(self):
        return self.name


class CollectionDocumentStatus(Base):
    __tablename__ = "collection_document_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

    def __repr__(self):
        return self.name

    @provide_session
    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
        }


class CollectionDocument(Base):
    __tablename__ = "collection_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_id = Column(Integer, ForeignKey("collections.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    status_id = Column(Integer, ForeignKey("collection_document_statuses.id"), nullable=False)

    collection: Mapped["Collection"] = relationship(back_populates="documents_link")
    document: Mapped["Document"] = relationship(back_populates="collections_link")
    status: Mapped["CollectionDocumentStatus"] = relationship()


class CollectionStatus(Base):
    __tablename__ = "collection_statuses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)

    collections: Mapped[List["Collection"]] = relationship(back_populates="status")

    def __repr__(self):
        return self.name

    @provide_session
    def to_dict(self, session=None):
        return {
            "id": self.id,
            "name": self.name,
        }


@basic_fields
class ChatbotConfiguration(Base):
    __tablename__ = "chatbot_configuration"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(Text, nullable=True)

    summary_prompt = Column(Text, nullable=True)
    analytic_topic_prompt = Column(Text, nullable=True)

    collection_id: Mapped[int] = Column(
        Integer,
        ForeignKey("collections.id"), nullable=True,
    )

    collection: Mapped["Collection"] = relationship(
        "Collection",
        back_populates="chatbot_configurations",
    )

    similar_threshold = Column(Float, nullable=False)
    temperature = Column(Float, nullable=False, default=0)
    max_completion_tokens = Column(Integer, nullable=False, default=0)

    limit_interval_seconds = Column(Integer, nullable=False, default=60)
    limit = Column(Integer, nullable=False, default=10)

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "prompt": self.prompt,
            "collection": self.collection.name,
            "similar_threshold": self.similar_threshold,
            "temperature": self.temperature,
            "max_completion_tokens": self.max_completion_tokens,
            "limit_interval_seconds": self.limit_interval_seconds,
            "limit": self.limit,
        }
