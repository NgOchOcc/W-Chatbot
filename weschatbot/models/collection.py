from typing import List

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, Float
from sqlalchemy.orm import Mapped, relationship

from weschatbot.models.base import Base, basic_fields
from weschatbot.utils.db import provide_session


@basic_fields
class Collection(Base):
    __tablename__ = 'collections'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    name = Column(String(63), nullable=False)

    status_id = Column(Integer, ForeignKey("collection_statuses.id"), nullable=False)
    status: Mapped["CollectionStatus"] = relationship(back_populates="collections")

    documents_link: Mapped[List["CollectionDocument"]] = relationship(back_populates="collection")

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

    collection_id: Mapped[int] = Column(
        Integer,
        ForeignKey("collections.id"), nullable=True,
    )

    collection: Mapped["Collection"] = relationship(
        "Collection",
        back_populates="chatbot_configurations",
    )

    similar_threshold = Column(Float, nullable=False)

    def to_dict(self, session=None):
        return {
            "id": self.id,
            "prompt": self.prompt,
            "collection": self.collection.name,
            "similar_threshold": self.similar_threshold,
        }
