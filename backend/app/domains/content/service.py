"""Subjects and legal pages, kept by admins (spec 7)."""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.auth.models import User, UserRole
from app.domains.content.models import (
    LegalDocument,
    LegalIn,
    LegalKind,
    LegalRead,
    LegalVersion,
    Subject,
    SubjectAdminView,
    SubjectIn,
    SubjectRead,
    subject_key,
)
from app.domains.notifications import service as notifications
from app.domains.tutors.models import TutorOffer, TutorOfferSubject

LEGAL_TITLES = {LegalKind.privacy: "privacy notice", LegalKind.terms: "terms of service",
                LegalKind.disclaimer: "disclaimer"}


# ---------- Subjects (R1) ----------

def offered_subjects(session: Session) -> list[SubjectRead]:
    """R1.6: what sign-up, offers, job posts and search filters offer, by group then name."""
    rows = session.exec(select(Subject).where(Subject.is_offered == True)  # noqa: E712
                        .order_by(Subject.group, Subject.name)).all()
    return [SubjectRead(name=s.name, group=s.group) for s in rows]


def offered(session: Session, names: list[str]) -> list[str]:
    """R1.5: each name once, in its listed spelling. A subject that isn't offered is a 422 naming it."""
    by_key = {s.key: s.name for s in session.exec(select(Subject).where(Subject.is_offered == True))}  # noqa: E712
    result = []
    for name in names:
        found = by_key.get(subject_key(name))
        if found is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                f"\"{name.strip()}\" isn't one of TutorLink's subjects. Choose one from the list.")
        if found not in result:
            result.append(found)
    return result


def all_names(session: Session) -> dict[str, str]:
    """Key to name for every subject, offered or removed: the exam still covers a removed subject for tutors who
    already teach it (R1.4), and never anything that isn't on the list (R1.5)."""
    return {s.key: s.name for s in session.exec(select(Subject))}


def admin_subjects(session: Session) -> list[SubjectAdminView]:
    """R1.2, with how many active offers teach each subject."""
    counts = dict(session.exec(
        select(TutorOfferSubject.subject, func.count())
        .join(TutorOffer, TutorOffer.id == TutorOfferSubject.offer_id)
        .where(TutorOffer.is_active == True)  # noqa: E712
        .group_by(TutorOfferSubject.subject)
    ).all())
    rows = session.exec(select(Subject).order_by(Subject.group, Subject.name)).all()
    return [SubjectAdminView(id=s.id, name=s.name, group=s.group, is_offered=s.is_offered,
                             offers=counts.get(s.name, 0)) for s in rows]


def _admin_view(session: Session, subject_id: UUID) -> SubjectAdminView:
    return next(v for v in admin_subjects(session) if v.id == subject_id)


def add_subject(session: Session, data: SubjectIn) -> SubjectAdminView:
    """R1.2, R1.3: a name already listed (offered or removed) is a 409."""
    key = subject_key(data.name)
    existing = session.exec(select(Subject).where(Subject.key == key)).first()
    if existing is not None:
        detail = (f"\"{existing.name}\" is already a subject" if existing.is_offered
                  else f"\"{existing.name}\" was removed. Restore it instead")
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    subject = Subject(name=data.name, key=key, group=data.group)
    session.add(subject)
    session.commit()
    return _admin_view(session, subject.id)


def set_offered(session: Session, subject_id: UUID, is_offered: bool) -> SubjectAdminView:
    """R1.4: removing hides the subject from new offers and jobs; existing ones keep it. Restoring undoes that."""
    subject = session.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subject not found")
    subject.is_offered = is_offered
    session.add(subject)
    session.commit()
    return _admin_view(session, subject.id)


# ---------- Legal pages (R2) ----------

def _latest(session: Session, kind: LegalKind) -> LegalDocument | None:
    return session.exec(select(LegalDocument).where(LegalDocument.kind == kind)
                        .order_by(LegalDocument.created_at.desc())).first()


def legal(session: Session, kind: LegalKind) -> LegalRead:
    """R2.3: the latest published version."""
    doc = _latest(session, kind)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"The {LEGAL_TITLES[kind]} hasn't been published yet")
    return LegalRead(kind=doc.kind, body=doc.body, published_at=doc.created_at)


def legal_versions(session: Session, kind: LegalKind) -> list[LegalVersion]:
    """R2.3: every version, newest first, with the email of the admin who published it (admins have no profile
    name). The starting versions have no publisher."""
    docs = list(session.exec(select(LegalDocument).where(LegalDocument.kind == kind)
                             .order_by(LegalDocument.created_at.desc())).all())
    ids = {d.published_by for d in docs if d.published_by}
    emails = dict(session.exec(select(User.id, User.email).where(User.id.in_(ids))).all()) if ids else {}
    return [LegalVersion(id=d.id, kind=d.kind, body=d.body, published_at=d.created_at,
                         published_by=emails.get(d.published_by)) for d in docs]


def publish_legal(session: Session, admin: User, kind: LegalKind, data: LegalIn) -> LegalRead:
    """R2.3, R2.4: a new version, shown at once; optionally every parent and tutor is told in the app."""
    doc = LegalDocument(kind=kind, body=data.body.strip(), published_by=admin.id)
    session.add(doc)
    if data.notify:
        title = LEGAL_TITLES[kind]
        user_ids = session.exec(select(User.id).where(User.role.in_([UserRole.parent, UserRole.tutor]),
                                                      User.is_active == True)).all()  # noqa: E712
        for user_id in user_ids:
            notifications.notify(session, user_id, f"We've updated our {title}",
                                 f"TutorLink's {title} has changed. Please take a moment to read it.",
                                 f"/{kind.value}", email=False)
    session.commit()
    session.refresh(doc)
    return LegalRead(kind=doc.kind, body=doc.body, published_at=doc.created_at)
