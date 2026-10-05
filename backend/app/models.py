from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    """Naive UTC timestamp (all DATETIME columns store UTC)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    permissions: Mapped[list] = mapped_column(JSON, default=list)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    username: Mapped[str] = mapped_column(String(100), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    role: Mapped[Role] = relationship(lazy="joined")


class Environment(Base):
    __tablename__ = "environments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    key: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    is_production: Mapped[bool] = mapped_column(Boolean, default=False)
    sdk_key: Mapped[str] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    creator: Mapped[Optional[User]] = relationship(lazy="joined")
    rollouts: Mapped[list["FeatureRollout"]] = relationship(
        back_populates="flag", cascade="all, delete-orphan", lazy="selectin"
    )


class FeatureRollout(Base):
    """Per-environment state of a flag: on/off, percentage, schedule, version."""
    __tablename__ = "feature_rollouts"
    __table_args__ = (UniqueConstraint("flag_id", "environment_id", name="uq_rollout_flag_env"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("feature_flags.id", ondelete="CASCADE"))
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=100)
    scheduled_enable_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    scheduled_disable_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    flag: Mapped[FeatureFlag] = relationship(back_populates="rollouts")
    environment: Mapped[Environment] = relationship(lazy="joined")


class UserAssignment(Base):
    __tablename__ = "user_assignments"
    __table_args__ = (UniqueConstraint("flag_id", "environment_id", "user_identifier", name="uq_assign"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("feature_flags.id", ondelete="CASCADE"))
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    user_identifier: Mapped[str] = mapped_column(String(255))
    access: Mapped[str] = mapped_column(String(10))  # allow | deny
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_flag_created", "flag_id", "created_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(100), default="system")
    action: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    flag_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # no FK: history survives deletes
    flag_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    environment_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    environment_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    before: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    after: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class FeatureUsage(Base):
    """Daily evaluation counters used by the analytics endpoints."""
    __tablename__ = "feature_usage"
    __table_args__ = (UniqueConstraint("flag_id", "environment_id", "usage_date", name="uq_usage"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("feature_flags.id", ondelete="CASCADE"))
    environment_id: Mapped[int] = mapped_column(ForeignKey("environments.id", ondelete="CASCADE"))
    usage_date: Mapped[date] = mapped_column(Date)
    evaluations: Mapped[int] = mapped_column(Integer, default=0)
    enabled_count: Mapped[int] = mapped_column(Integer, default=0)
