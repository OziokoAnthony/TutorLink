"""Subjects and legal pages, kept by admins (spec 7), and parents' and tutors' agreement to them (spec 9)."""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlmodel import Session, select

from app.domains.auth.models import User, UserRole
from app.domains.content.models import (
    AcceptLegalIn,
    LegalAcceptance,
    LegalAudience,
    LegalDocument,
    LegalIn,
    LegalKind,
    LegalRead,
    LegalVersion,
    MyLegal,
    MyLegalDocument,
    Subject,
    SubjectAdminView,
    SubjectIn,
    SubjectRead,
    subject_key,
)
from app.domains.notifications import service as notifications
from app.domains.tutors.models import TutorOffer, TutorOfferSubject, TutorProfile, VettingStatus

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


# ---------- Legal pages (spec 7 R2, spec 9 R1) ----------

AUDIENCE_WORDS = {LegalAudience.parent: "parents'", LegalAudience.tutor: "tutors'"}


def _latest(session: Session, audience: LegalAudience, kind: LegalKind) -> LegalDocument | None:
    return session.exec(select(LegalDocument).where(LegalDocument.audience == audience, LegalDocument.kind == kind)
                        .order_by(LegalDocument.created_at.desc())).first()


def _read(doc: LegalDocument) -> LegalRead:
    return LegalRead(audience=doc.audience, kind=doc.kind, body=doc.body, published_at=doc.created_at)


def legal(session: Session, audience: LegalAudience, kind: LegalKind) -> LegalRead:
    """The latest published version (spec 7 R2.3)."""
    doc = _latest(session, audience, kind)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            f"The {AUDIENCE_WORDS[audience]} {LEGAL_TITLES[kind]} hasn't been published yet")
    return _read(doc)


def legal_versions(session: Session, audience: LegalAudience, kind: LegalKind) -> list[LegalVersion]:
    """Every version, newest first, with the email of the admin who published it. The starting versions have no
    publisher."""
    docs = list(session.exec(select(LegalDocument)
                             .where(LegalDocument.audience == audience, LegalDocument.kind == kind)
                             .order_by(LegalDocument.created_at.desc())).all())
    ids = {d.published_by for d in docs if d.published_by}
    emails = dict(session.exec(select(User.id, User.email).where(User.id.in_(ids))).all()) if ids else {}
    return [LegalVersion(id=d.id, audience=d.audience, kind=d.kind, body=d.body, published_at=d.created_at,
                         published_by=emails.get(d.published_by)) for d in docs]


def publish_legal(session: Session, admin: User, audience: LegalAudience, kind: LegalKind,
                  data: LegalIn) -> LegalRead:
    """A new version, shown at once, which everyone in its audience must agree to (spec 9 R5.1). Optionally they're
    told in the app (spec 7 R2.4)."""
    doc = LegalDocument(audience=audience, kind=kind, body=data.body.strip(), published_by=admin.id)
    session.add(doc)
    if data.notify:
        title = LEGAL_TITLES[kind]
        role = UserRole.parent if audience == LegalAudience.parent else UserRole.tutor
        user_ids = session.exec(select(User.id).where(User.role == role, User.is_active == True)).all()  # noqa: E712
        for user_id in user_ids:
            notifications.notify(session, user_id, f"We've updated our {title}",
                                 f"TutorLink's {title} has changed. Please take a moment to read it.",
                                 f"/{kind.value}", email=False)
    session.commit()
    session.refresh(doc)
    return _read(doc)


# ---------- Agreeing (spec 9 R2-R5) ----------

def audience_of(user: User) -> LegalAudience | None:
    """Admins agree to nothing (R6.1)."""
    return {UserRole.parent: LegalAudience.parent, UserRole.tutor: LegalAudience.tutor}.get(user.role)


def _latest_documents(session: Session, audience: LegalAudience) -> list[LegalDocument]:
    """The latest version of each kind, in one query: this runs on every parent and tutor request (deps)."""
    return list(session.exec(select(LegalDocument).where(LegalDocument.audience == audience)
                             .distinct(LegalDocument.kind)
                             .order_by(LegalDocument.kind, LegalDocument.created_at.desc())).all())


def _accepted(session: Session, user_id: UUID, doc_ids: list[UUID]) -> dict[UUID, datetime]:
    if not doc_ids:
        return {}
    return dict(session.exec(select(LegalAcceptance.document_id, LegalAcceptance.created_at)
                             .where(LegalAcceptance.user_id == user_id,
                                    LegalAcceptance.document_id.in_(doc_ids))).all())


def _has_agreed_before(session: Session, user_id: UUID) -> bool:
    return session.exec(select(LegalAcceptance.id).where(LegalAcceptance.user_id == user_id)).first() is not None


def _approved_tutor(session: Session, user_id: UUID) -> bool:
    status_ = session.exec(select(TutorProfile.vetting_status).where(TutorProfile.user_id == user_id)).first()
    return status_ == VettingStatus.approved


def has_agreed(session: Session, user: User) -> bool:
    """Agreed to the latest version of every one of their documents."""
    audience = audience_of(user)
    if audience is None:
        return True
    docs = _latest_documents(session, audience)
    accepted = _accepted(session, user.id, [d.id for d in docs])
    return all(d.id in accepted for d in docs)


def must_agree_now(session: Session, user: User) -> bool:
    """R3, R5.2: a parent, or a tutor who agreed before or is approved, who hasn't agreed to the latest versions
    can't continue. A tutor who never agreed is only held back from approval (R4)."""
    if has_agreed(session, user):
        return False
    if user.role == UserRole.parent:
        return True
    return _has_agreed_before(session, user.id) or _approved_tutor(session, user.id)


def _can_accept(session: Session, user: User) -> bool:
    """R4.1: a tutor agrees as the last onboarding step, once the others are done."""
    if user.role != UserRole.tutor or _has_agreed_before(session, user.id) or _approved_tutor(session, user.id):
        return True
    from app.domains.onboarding import service as onboarding  # onboarding asks has_agreed, so imported here
    return onboarding.ready_to_agree(session, user)


def my_legal(session: Session, user: User) -> MyLegal:
    """R2.4: the reader's three latest documents and when they agreed to each."""
    audience = audience_of(user)
    docs = _latest_documents(session, audience)
    accepted = _accepted(session, user.id, [d.id for d in docs])
    return MyLegal(required=must_agree_now(session, user), can_accept=_can_accept(session, user),
                   documents=[MyLegalDocument(id=d.id, audience=d.audience, kind=d.kind, body=d.body,
                                              published_at=d.created_at, accepted_at=accepted.get(d.id))
                              for d in docs])


def accept_legal(session: Session, user: User, data: AcceptLegalIn, ip: str | None) -> MyLegal:
    """R2.1-R2.3: agreeing to all three latest documents at once, stored as proof."""
    docs = _latest_documents(session, audience_of(user))
    if not docs or set(data.document_ids) != {d.id for d in docs}:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "These documents have changed since you opened them. Please read the latest versions.")
    if not _can_accept(session, user):
        raise HTTPException(status.HTTP_409_CONFLICT, "Finish the other onboarding steps first, then agree.")
    accepted = _accepted(session, user.id, [d.id for d in docs])
    for doc in docs:
        if doc.id not in accepted:
            session.add(LegalAcceptance(user_id=user.id, document_id=doc.id, ip=ip))
    session.commit()
    return my_legal(session, user)
