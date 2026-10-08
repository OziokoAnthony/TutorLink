"""Imports every table model so SQLModel.metadata knows all tables (Alembic and tests use it)."""

from app.domains.auth import models as auth_models  # noqa: F401
from app.domains.bookings import models as bookings_models  # noqa: F401
from app.domains.fees import models as fees_models  # noqa: F401
from app.domains.job_posts import models as job_posts_models  # noqa: F401
from app.domains.lessons import models as lessons_models  # noqa: F401
from app.domains.notifications import models as notifications_models  # noqa: F401
from app.domains.payments import models as payments_models  # noqa: F401
from app.domains.payouts import models as payouts_models  # noqa: F401
from app.domains.reviews import models as reviews_models  # noqa: F401
from app.domains.tutors import models as tutors_models  # noqa: F401
from app.domains.webhooks import models as webhooks_models  # noqa: F401
