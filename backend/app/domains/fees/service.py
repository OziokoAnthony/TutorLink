from decimal import Decimal

from sqlmodel import Session

from app.core.clock import money
from app.db.base import utcnow
from app.domains.auth.models import User
from app.domains.fees.models import FeesRead, FeesUpdate, PlatformFees


def current(session: Session) -> PlatformFees:
    fees = session.get(PlatformFees, 1)
    if fees is None:  # seeded by migration 0008; recreated if someone deleted it
        fees = PlatformFees(id=1, parent_fee_rate=Decimal("0.1000"), tutor_fee_rate=Decimal("0.0800"))
        session.add(fees)
        session.flush()
    return fees


def update(session: Session, admin: User, data: FeesUpdate) -> FeesRead:
    fees = current(session)
    fees.parent_fee_rate = data.parent_fee_rate
    fees.tutor_fee_rate = data.tutor_fee_rate
    fees.updated_by = admin.id
    fees.updated_at = utcnow()
    session.add(fees)
    session.commit()
    session.refresh(fees)
    return FeesRead.model_validate(fees)


def parent_price(price: Decimal, parent_fee_rate: Decimal) -> Decimal:
    """What the parent pays per lesson: the agreed price plus the parent fee."""
    return money(price * (1 + parent_fee_rate))


def tutor_earning(price: Decimal, tutor_fee_rate: Decimal) -> Decimal:
    """What the tutor receives per lesson: the agreed price minus the tutor fee."""
    return money(price * (1 - tutor_fee_rate))
