"""Subjects and legal pages kept by admins (spec 7)

The subject list moves from code into `subjects`, seeded with the subjects TutorLink started with. The privacy
notice, terms and the new disclaimer move into `legal_documents`, one row per published version, seeded with the
drafts. The texts are copied here, not imported, so this migration never changes.

Revision ID: 0023
Revises: 0022
Create Date: 2026-10-11
"""
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

subject_group = postgresql.ENUM("nigerian", "international", name="subject_group", create_type=False)
legal_kind = postgresql.ENUM("privacy", "terms", "disclaimer", name="legal_kind", create_type=False)

NIGERIAN = (
    "Mathematics", "English Language", "Basic Science", "Basic Technology", "Social Studies",
    "Civic Education", "Physics", "Chemistry", "Biology", "Further Mathematics", "Economics",
    "Literature in English", "Government", "Geography", "Agricultural Science", "Computer Studies",
    "Commerce", "Accounting", "French", "Yoruba", "Igbo", "Hausa", "Christian Religious Studies",
    "Islamic Religious Studies", "Verbal Reasoning", "Quantitative Reasoning",
)
INTERNATIONAL = (
    "Additional Mathematics", "Statistics", "Combined Science", "Computer Science", "Business Studies",
    "History", "Global Perspectives", "Environmental Management", "Psychology", "Sociology",
    "English as a Second Language", "Spanish", "German", "Mandarin Chinese", "Art and Design",
    "Design and Technology", "Music", "Physical Education", "IB Theory of Knowledge",
    "AP Calculus", "SAT", "ACT", "IELTS", "TOEFL",
)

PRIVACY = """TutorLink is run by [company name to be filled in], [address to be filled in] ("TutorLink", "we"). We decide how your personal data is used, and this notice explains it under the Nigeria Data Protection Act 2023. Questions or requests: **[contact email to be filled in]**.

## What we collect

- **Everyone:** name, email, phone (if given), password (stored only as a one-way hash) or your Google sign-in, profile picture, notifications, and any feedback or help chats you send to our team.
- **Parents:** home address (if given), your child's strengths and weaknesses as you describe them in bookings and job posts, bookings, payments into your TutorLink account number, your balance, withdrawals and the bank account you withdraw to, problem reports and reviews.
- **Tutors:** the areas you cover, your offers and availability, your bio, certificates and their details, quiz results, lesson reports, earnings and your payout bank account.
- **NIN checks (tutors):** you give your NIN and take a selfie, which we send to our verification provider. We keep only whether each check passed, the last 4 digits of the NIN, a one-way code that stops one NIN verifying two accounts, and the provider's reference. We don't keep your full NIN, your selfie or the NIN photo.
- **WAEC/NECO result-checker PINs:** stored encrypted and deleted once we've reviewed the certificate.
- **Online lesson recordings:** online lessons are recorded, with the parent's agreement, and may show the child.
- **Technical data:** your IP address, used to limit repeated login and sign-up attempts, and the login cookie that keeps you signed in. We don't use advertising or tracking cookies.

## Why we use it

- To run the service you signed up for: matching parents and tutors, bookings, lessons, payments, refunds and payouts (performing our contract with you).
- To vet tutors before parents see them, which keeps children safe and is why we check NINs, certificates and quiz results (our legitimate interest, and your consent when you start the check).
- To record online lessons so problems can be reviewed (the parent's consent when booking).
- To keep accounts and payments secure, and to keep the financial records the law requires (legal obligation and legitimate interest).
- To answer your feedback and questions.

## Who else handles it

We share data only with the services that help us run TutorLink, and only what each one needs:

- **Paystack:** your TutorLink account number, deposits, withdrawals and tutor payouts.
- **Dojah:** NIN and selfie checks for tutors.
- **Google:** signing in with Google, if you choose it.
- **Resend:** sending our emails.
- **Anthropic (Claude):** writes quiz questions, and answers questions you type into the help chat. The help assistant sees only what you type there, not your account.
- **Our file storage provider:** pictures, certificates and lesson recordings, kept private.

Some of these providers process data outside Nigeria. Where they do, we rely on the safeguards the Act allows. Within TutorLink, parents and tutors see only what they need: a tutor sees a parent's first name and picture on job posts, and the home address only once an at-home booking is paid. We don't sell your data.

## How long we keep it

- Online lesson recordings: deleted 90 days after the lesson, unless a problem reported on that lesson is still open.
- Password reset links: work once, for one hour.
- Account, booking and payment records: while your account is open, then for as long as the law requires us to keep financial records.

## Your rights

You can ask us for a copy of your data, to correct it, to delete it (except records we must keep by law), to restrict or object to how we use it, or to withdraw consent you gave. Write to **[contact email to be filled in]** and we'll reply within 30 days. You can also complain to the Nigeria Data Protection Commission (ndpc.gov.ng).

## Children

Accounts are for adults: parents, guardians and tutors aged 18 or over. Information about a child is given by their parent, who decides what to share.

## Changes

If we change this notice, we'll tell you in the app."""

TERMS = """These terms are an agreement between you and [company name to be filled in], [address to be filled in] ("TutorLink"), for using TutorLink. By creating an account you accept them and our privacy notice.

## 1. What TutorLink does

TutorLink connects parents with tutors for lessons at home or online, takes payment before lessons and pays tutors after them. Tutors are independent: they aren't TutorLink's employees, and each tutor is responsible for the lessons they give.

## 2. Your account

- You must be 18 or over, and give true details. Tutors must register in their name exactly as on their NIN record.
- Keep your password private. You're responsible for what happens in your account.
- We may suspend an account that breaks these terms, puts a child at risk or is used for fraud.

## 3. Tutors

- Before parents can see you, you must verify your NIN, have a certificate verified by us, pass the qualifying quiz and be approved. We may refuse or withdraw approval.
- Answer booking requests within 72 hours, turn up to every paid lesson, and submit each lesson's report within 24 hours. Online lessons need their recording uploaded before the report.
- An earning becomes payable 24 hours after your report if the parent reports no problem, and is paid to your bank account 48 hours after the last lesson of its billing period. TutorLink's fee is deducted from the lesson price, and your dashboard shows exactly what you'll receive.

## 4. Parents: booking and paying

- You pay by bank transfer into your own TutorLink account number. We don't take cards. The price you see includes TutorLink's fee, and you always see the full amount before paying.
- Money you send becomes your TutorLink balance, which pays due billing periods automatically, oldest first.
- The first period must be paid at least 24 hours before its first lesson, or the booking is released. Each later period must be paid 24 hours before its first lesson, or the booking pauses; a booking paused for 7 days ends.
- You can withdraw your balance to your bank account. We process withdrawals by hand.

## 5. Cancelling, problems and refunds

- If you cancel with at least 48 hours' notice before a paid lesson, lessons 48 or more hours away are refunded to your balance once we approve it. The refund is the lesson price, not TutorLink's fee. Lessons sooner than that go ahead as normal.
- If something goes wrong with a lesson (the tutor didn't come, came late or left early, or broke what was agreed), report it from the lesson, until 24 hours after the tutor's report. We then refund the lesson to your balance, reschedule it, or let it stand.

## 6. Recordings

Online lessons are recorded so problems can be reviewed. Only the parent, the tutor and TutorLink can watch a recording, and it's deleted 90 days after the lesson unless a problem on it is still open. Don't copy or share recordings.

## 7. Behaving well

- Treat each other with respect, and keep children safe at all times.
- Don't post anything false, offensive or unlawful, or use someone else's identity or documents.
- Don't try to break, overload or get around the security of TutorLink.

## 8. Help assistant

The help chat's answers come from an AI assistant and may be wrong. They don't change these terms or your bookings. For anything about your own account, send the conversation to our team.

## 9. Our responsibility

We vet tutors carefully, but we can't guarantee a child's results. As far as the law allows, we're not liable for indirect losses, and our liability for any booking is limited to what you paid TutorLink for it. Nothing in these terms takes away rights you have under Nigerian consumer law. See also our disclaimer.

## 10. Changes and the law

If we change these terms, we'll tell you in the app. These terms are governed by the laws of the Federal Republic of Nigeria. Questions: **[contact email to be filled in]**."""

DISCLAIMER = """This disclaimer explains the limits of what TutorLink, run by [company name to be filled in], provides. It's part of our terms of service.

## TutorLink is a marketplace

TutorLink connects parents with independent tutors. Tutors aren't our employees, and each tutor is responsible for how they teach. We check every tutor's NIN, a certificate and a qualifying quiz before parents can see them, but these checks can't guarantee how any tutor will behave or teach.

## No guaranteed results

Lessons can help a child learn, but we don't promise any grade, exam result, admission or other outcome.

## Keeping children safe

Parents and guardians remain responsible for their children's safety, including during lessons at home. If something worries you, end the lesson and report it to us straight away.

## The help assistant

The help chat's answers are written by an AI assistant (Claude, by Anthropic) from general information about TutorLink. They may be wrong or out of date, they aren't advice, and they don't change our terms, your bookings or your payments. For anything about your own account, send the conversation to our team.

## Other services

Video calls, banks, Paystack, Google and other services used alongside TutorLink are run by others, under their own terms. We aren't responsible for their availability or for what they do.

## Information on TutorLink

Tutor profiles, bios and reviews are written by tutors and parents, not by us. We try to keep the rest of the site accurate, but it's general information and may change.

## Liability

What we're responsible for, and its limits, is set out in section 9 of our terms of service. Questions: **[contact email to be filled in]**."""


def upgrade() -> None:
    subject_group.create(op.get_bind(), checkfirst=True)
    legal_kind.create(op.get_bind(), checkfirst=True)
    subjects = op.create_table(
        "subjects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("key", sa.String(length=60), nullable=False),
        sa.Column("group", subject_group, nullable=False),
        sa.Column("is_offered", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_subjects"),
        sa.UniqueConstraint("key", name="uq_subjects_key"),
    )
    legal = op.create_table(
        "legal_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", legal_kind, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("published_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], name="fk_legal_documents_published_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_legal_documents"),
    )
    op.create_index("ix_legal_documents_kind", "legal_documents", ["kind"])

    now = datetime.now(timezone.utc)
    op.bulk_insert(subjects, [
        {"id": uuid.uuid4(), "created_at": now, "updated_at": now, "name": name, "key": " ".join(name.lower().split()),
         "group": group, "is_offered": True}
        for group, names in (("nigerian", NIGERIAN), ("international", INTERNATIONAL)) for name in names
    ])
    op.bulk_insert(legal, [
        {"id": uuid.uuid4(), "created_at": now, "updated_at": now, "kind": kind, "body": body, "published_by": None}
        for kind, body in (("privacy", PRIVACY), ("terms", TERMS), ("disclaimer", DISCLAIMER))
    ])


def downgrade() -> None:
    op.drop_index("ix_legal_documents_kind", table_name="legal_documents")
    op.drop_table("legal_documents")
    op.drop_table("subjects")
    legal_kind.drop(op.get_bind(), checkfirst=True)
    subject_group.drop(op.get_bind(), checkfirst=True)
