from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("owner_id", "doi", name="uq_items_owner_doi"),
        Index("ix_items_owner_title", "owner_id", "title"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    container_title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    volume: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    issue: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    pages: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(
        String(8), nullable=True, default="zh"
    )
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    authors: Mapped[list["ItemAuthor"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class Author(Base):
    __tablename__ = "authors"
    __table_args__ = (
        Index("ix_authors_family_given", "family_name", "given_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    given_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    family_name: Mapped[str] = mapped_column(String(64), nullable=False)

    items: Mapped[list["ItemAuthor"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )


class ItemAuthor(Base):
    __tablename__ = "item_authors"

    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"), primary_key=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    item: Mapped["Item"] = relationship(back_populates="authors")
    author: Mapped["Author"] = relationship(back_populates="items")