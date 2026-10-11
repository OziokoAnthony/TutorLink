from datetime import datetime
from enum import Enum
from uuid import UUID

import sqlalchemy as sa
from pydantic import model_validator
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

from app.db.base import BaseUUIDModel, pg_enum


class FeedbackKind(str, Enum):
    problem = "problem"
    suggestion = "suggestion"
    praise = "praise"
    question = "question"


class ChatRole(str, Enum):
    user = "user"
    assistant = "assistant"


# ---------- Tables ----------

class Feedback(BaseUUIDModel, table=True):
    """A parent's or tutor's message to TutorLink (spec 6 R1), answered once by an admin (R2)."""

    __tablename__ = "feedback"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    kind: FeedbackKind = Field(sa_type=pg_enum(FeedbackKind, "feedback_kind"))
    message: str = Field(sa_type=sa.Text)
    # A help chat sent to the team (R3.4): [{"role": "user" | "assistant", "content": "..."}], as the browser sent it.
    transcript: list[dict] | None = Field(default=None, sa_type=JSONB)
    reply: str | None = Field(default=None, sa_type=sa.Text)
    replied_at: datetime | None = Field(default=None, sa_type=sa.DateTime(timezone=True))
    replied_by: UUID | None = Field(default=None, foreign_key="users.id")


# ---------- DTOs ----------

class ChatMessage(SQLModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=4000)  # R3.5


class FeedbackIn(SQLModel):
    kind: FeedbackKind
    message: str = Field(min_length=10, max_length=2000)  # R1.1
    transcript: list[ChatMessage] | None = Field(default=None, max_length=40)


class FeedbackReplyIn(SQLModel):
    reply: str = Field(min_length=3, max_length=2000)  # R2.3


class FeedbackRead(SQLModel):
    """What the sender sees."""

    id: UUID
    kind: FeedbackKind
    message: str
    transcript: list[ChatMessage] | None
    reply: str | None
    replied_at: datetime | None
    created_at: datetime


class FeedbackAdminView(FeedbackRead):
    user_id: UUID
    user_name: str | None
    user_email: str
    user_role: str


class HelpChatIn(SQLModel):
    """The whole conversation so far, kept by the browser (R3.5). It starts and ends with the user."""

    messages: list[ChatMessage] = Field(min_length=1, max_length=40)

    @model_validator(mode="after")
    def _user_turns(self):
        if self.messages[0].role != ChatRole.user or self.messages[-1].role != ChatRole.user:
            raise ValueError("The conversation must start and end with your message")
        return self


class HelpChatOut(SQLModel):
    reply: str
