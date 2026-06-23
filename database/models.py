"""SQLAlchemy models and session lifecycle for the review engine."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Index, Integer, String, Text, UniqueConstraint, create_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# NOTE: Engine is now created and managed by database.connection module
# This ensures a single point of control for database connections
# Use get_engine() and get_session_factory() from database.connection instead


class Base(DeclarativeBase):
    pass


class ReviewModel(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_review_source_external_id"),
        Index("ix_reviews_source_theme", "source", "theme"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(String(50), index=True)
    app_name: Mapped[str] = mapped_column(String(255), index=True)
    reviewer: Mapped[str] = mapped_column(String(255), default="Unknown")
    rating: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text: Mapped[str] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    theme: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    theme_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ThemeModel(Base):
    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    theme_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    top_reviews: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
