from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel


# ---------- Tables ----------

class Notification(BaseUUIDModel, table=True):
    """An in-app notification. The same message is usually also emailed."""

    __tablename__ = "notifications"
    __table_args__ = (sa.Index("ix_notifications_user_id_created_at", "user_id", "created_at"),)

    user_id: UUID = Field(foreign_key="users.id")
    title: str
    body: str = Field(sa_type=sa.Text)
    link: str | None = None  # frontend path, e.g. /dashboard/parent/bookings
    read_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))


# ---------- DTOs ----------

class NotificationRead(SQLModel):
    id: UUID
    title: str
    body: str
    link: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(SQLModel):
    unread_count: int
    items: list[NotificationRead]
