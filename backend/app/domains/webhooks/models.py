from datetime import datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlmodel import Field, SQLModel


class WebhookEvent(SQLModel, table=True):
    """Idempotency log for Paystack webhooks. Columns exactly as in CLAUDE.md (no created/updated_at)."""

    __tablename__ = "webhook_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: str = Field(unique=True)
    event_type: str
    processed_at: datetime = Field(sa_type=sa.DateTime(timezone=True))
