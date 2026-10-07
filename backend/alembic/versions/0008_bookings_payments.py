"""Marketplace: tutor offers, bookings, prepaid bank-transfer payments, lessons, payouts (spec 1)

Replaces the monthly-invoice flow (schedules, sessions, invoices, invoice_items, tutor_subjects).
There is no production data, so the old tables are dropped rather than migrated.

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-07
"""
import importlib.util
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

payout_method = postgresql.ENUM('paystack', 'manual', name="payout_method", create_type=False)
transfer_status = postgresql.ENUM('pending', 'processing', 'paid', 'failed', 'rejected', name="transfer_status", create_type=False)
education_level = postgresql.ENUM('primary', 'junior_secondary', 'senior_secondary', name="education_level", create_type=False)
lesson_mode = postgresql.ENUM('online', 'offline', name="lesson_mode", create_type=False)
billing_period = postgresql.ENUM('daily', 'weekly', 'monthly', name="billing_period", create_type=False)
booking_status = postgresql.ENUM('requested', 'accepted', 'active', 'paused', 'ended', 'declined', 'expired', 'released', 'cancelled', name="booking_status", create_type=False)
period_status = postgresql.ENUM('due', 'paid', 'missed', 'expired', 'void', name="period_status", create_type=False)
refund_reason = postgresql.ENUM('cancellation', 'lesson_issue', name="refund_reason", create_type=False)
refund_status = postgresql.ENUM('pending', 'approved', 'rejected', name="refund_status", create_type=False)
lesson_status = postgresql.ENUM('confirmed', 'reported', 'completed', 'disputed', 'flagged', 'refunded', 'cancelled', name="lesson_status", create_type=False)
earning_status = postgresql.ENUM('pending', 'on_hold', 'payable', 'paid', 'void', name="earning_status", create_type=False)
wallet_entry_kind = postgresql.ENUM('deposit', 'period_payment', 'refund', 'withdrawal', 'withdrawal_reversal', name="wallet_entry_kind", create_type=False)
issue_kind = postgresql.ENUM('tutor_absent', 'late_or_left_early', 'agreement_broken', 'other', 'no_report', name="issue_kind", create_type=False)
issue_resolution = postgresql.ENUM('refund', 'reschedule', 'reject', name="issue_resolution", create_type=False)

NEW_ENUMS = [payout_method, transfer_status, lesson_mode, billing_period, booking_status, period_status, refund_reason, refund_status, lesson_status, earning_status, wallet_entry_kind, issue_kind, issue_resolution]


def upgrade() -> None:
    # Old monthly-invoice flow (migrations 0002-0005), dropped in dependency order.
    op.drop_table("invoice_items")
    op.drop_table("invoices")
    op.drop_table("sessions")
    op.drop_table("schedules")
    op.drop_table("tutor_subjects")
    postgresql.ENUM(name="invoice_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="session_status").drop(op.get_bind(), checkfirst=True)
    op.drop_column("tutor_profiles", "rate_per_session")
    op.add_column("users", sa.Column("photo_key", sa.String(), nullable=True))

    for enum in NEW_ENUMS:
        enum.create(op.get_bind(), checkfirst=True)

    op.create_table('notifications',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('title', sa.String(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('link', sa.String(), nullable=True),
    sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_notifications_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_notifications'))
    )
    op.create_index('ix_notifications_user_id_created_at', 'notifications', ['user_id', 'created_at'], unique=False)
    op.create_table('payouts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tutor_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('lesson_count', sa.Integer(), nullable=False),
    sa.Column('method', payout_method, nullable=False),
    sa.Column('status', transfer_status, nullable=False),
    sa.Column('reference', sa.String(), nullable=False),
    sa.Column('transfer_code', sa.String(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('created_by', sa.Uuid(), nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_payouts_created_by_users')),
    sa.ForeignKeyConstraint(['tutor_id'], ['users.id'], name=op.f('fk_payouts_tutor_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payouts')),
    sa.UniqueConstraint('reference', name=op.f('uq_payouts_reference'))
    )
    op.create_index(op.f('ix_payouts_tutor_id'), 'payouts', ['tutor_id'], unique=False)
    op.create_table('platform_fees',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('parent_fee_rate', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('tutor_fee_rate', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('updated_by', sa.Uuid(), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('id = 1', name=op.f('ck_platform_fees_single_row')),
    sa.ForeignKeyConstraint(['updated_by'], ['users.id'], name=op.f('fk_platform_fees_updated_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_platform_fees'))
    )
    op.create_table('tutor_bank_accounts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tutor_id', sa.Uuid(), nullable=False),
    sa.Column('bank_code', sa.String(), nullable=False),
    sa.Column('bank_name', sa.String(), nullable=False),
    sa.Column('account_number', sa.String(), nullable=False),
    sa.Column('account_name', sa.String(), nullable=False),
    sa.Column('name_matches', sa.Boolean(), nullable=False),
    sa.Column('override_note', sa.Text(), nullable=True),
    sa.Column('overridden_by', sa.Uuid(), nullable=True),
    sa.Column('recipient_code', sa.String(), nullable=True),
    sa.ForeignKeyConstraint(['overridden_by'], ['users.id'], name=op.f('fk_tutor_bank_accounts_overridden_by_users')),
    sa.ForeignKeyConstraint(['tutor_id'], ['users.id'], name=op.f('fk_tutor_bank_accounts_tutor_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tutor_bank_accounts')),
    sa.UniqueConstraint('tutor_id', name=op.f('uq_tutor_bank_accounts_tutor_id'))
    )
    op.create_table('tutor_offers',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('tutor_id', sa.Uuid(), nullable=False),
    sa.Column('level', education_level, nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.ForeignKeyConstraint(['tutor_id'], ['users.id'], name=op.f('fk_tutor_offers_tutor_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tutor_offers'))
    )
    op.create_index(op.f('ix_tutor_offers_tutor_id'), 'tutor_offers', ['tutor_id'], unique=False)
    op.create_table('virtual_accounts',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('customer_code', sa.String(), nullable=False),
    sa.Column('account_number', sa.String(), nullable=False),
    sa.Column('account_name', sa.String(), nullable=False),
    sa.Column('bank_name', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], name=op.f('fk_virtual_accounts_parent_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_virtual_accounts')),
    sa.UniqueConstraint('customer_code', name=op.f('uq_virtual_accounts_customer_code')),
    sa.UniqueConstraint('parent_id', name=op.f('uq_virtual_accounts_parent_id'))
    )
    op.create_table('withdrawals',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('bank_code', sa.String(), nullable=False),
    sa.Column('bank_name', sa.String(), nullable=False),
    sa.Column('account_number', sa.String(), nullable=False),
    sa.Column('account_name', sa.String(), nullable=False),
    sa.Column('status', transfer_status, nullable=False),
    sa.Column('reference', sa.String(), nullable=False),
    sa.Column('transfer_code', sa.String(), nullable=True),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('processed_by', sa.Uuid(), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], name=op.f('fk_withdrawals_parent_id_users')),
    sa.ForeignKeyConstraint(['processed_by'], ['users.id'], name=op.f('fk_withdrawals_processed_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_withdrawals')),
    sa.UniqueConstraint('reference', name=op.f('uq_withdrawals_reference'))
    )
    op.create_index(op.f('ix_withdrawals_parent_id'), 'withdrawals', ['parent_id'], unique=False)
    op.create_table('bookings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('tutor_id', sa.Uuid(), nullable=False),
    sa.Column('offer_id', sa.Uuid(), nullable=True),
    sa.Column('subjects', postgresql.ARRAY(sa.String()), nullable=False),
    sa.Column('level', education_level, nullable=False),
    sa.Column('mode', lesson_mode, nullable=False),
    sa.Column('billing_period', billing_period, nullable=False),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('parent_fee_rate', sa.Numeric(precision=5, scale=4), nullable=True),
    sa.Column('tutor_fee_rate', sa.Numeric(precision=5, scale=4), nullable=True),
    sa.Column('child_strengths', sa.Text(), nullable=False),
    sa.Column('child_weaknesses', sa.Text(), nullable=False),
    sa.Column('status', booking_status, server_default='requested', nullable=False),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('paused_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('close_note', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['offer_id'], ['tutor_offers.id'], name=op.f('fk_bookings_offer_id_tutor_offers')),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], name=op.f('fk_bookings_parent_id_users')),
    sa.ForeignKeyConstraint(['tutor_id'], ['users.id'], name=op.f('fk_bookings_tutor_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bookings'))
    )
    op.create_index(op.f('ix_bookings_parent_id'), 'bookings', ['parent_id'], unique=False)
    op.create_index(op.f('ix_bookings_tutor_id'), 'bookings', ['tutor_id'], unique=False)
    op.create_table('tutor_offer_subjects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('offer_id', sa.Uuid(), nullable=False),
    sa.Column('subject', sa.String(), nullable=False),
    sa.ForeignKeyConstraint(['offer_id'], ['tutor_offers.id'], name=op.f('fk_tutor_offer_subjects_offer_id_tutor_offers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tutor_offer_subjects')),
    sa.UniqueConstraint('offer_id', 'subject', name=op.f('uq_tutor_offer_subjects_offer_id_subject'))
    )
    op.create_table('tutor_offer_windows',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('offer_id', sa.Uuid(), nullable=False),
    sa.Column('day_of_week', sa.SmallInteger(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.ForeignKeyConstraint(['offer_id'], ['tutor_offers.id'], name=op.f('fk_tutor_offer_windows_offer_id_tutor_offers')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_tutor_offer_windows'))
    )
    op.create_index(op.f('ix_tutor_offer_windows_offer_id'), 'tutor_offer_windows', ['offer_id'], unique=False)
    op.create_table('booking_periods',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('booking_id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('starts_on', sa.Date(), nullable=False),
    sa.Column('ends_on', sa.Date(), nullable=False),
    sa.Column('lesson_count', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('first_lesson_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_lesson_end_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', period_status, server_default='due', nullable=False),
    sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_booking_periods_booking_id_bookings')),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], name=op.f('fk_booking_periods_parent_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_booking_periods')),
    sa.UniqueConstraint('booking_id', 'starts_on', name=op.f('uq_booking_periods_booking_id_starts_on'))
    )
    op.create_index(op.f('ix_booking_periods_parent_id'), 'booking_periods', ['parent_id'], unique=False)
    op.create_table('booking_slots',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('booking_id', sa.Uuid(), nullable=False),
    sa.Column('day_of_week', sa.SmallInteger(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_booking_slots_booking_id_bookings')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_booking_slots'))
    )
    op.create_index(op.f('ix_booking_slots_booking_id'), 'booking_slots', ['booking_id'], unique=False)
    op.create_table('refunds',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('booking_id', sa.Uuid(), nullable=False),
    sa.Column('reason', refund_reason, nullable=False),
    sa.Column('lesson_count', sa.Integer(), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('status', refund_status, nullable=False),
    sa.Column('note', sa.Text(), nullable=True),
    sa.Column('decided_by', sa.Uuid(), nullable=True),
    sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_refunds_booking_id_bookings')),
    sa.ForeignKeyConstraint(['decided_by'], ['users.id'], name=op.f('fk_refunds_decided_by_users')),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], name=op.f('fk_refunds_parent_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_refunds'))
    )
    op.create_index(op.f('ix_refunds_parent_id'), 'refunds', ['parent_id'], unique=False)
    op.create_table('lessons',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('booking_id', sa.Uuid(), nullable=False),
    sa.Column('period_id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('tutor_id', sa.Uuid(), nullable=False),
    sa.Column('lesson_date', sa.Date(), nullable=False),
    sa.Column('start_time', sa.Time(), nullable=False),
    sa.Column('end_time', sa.Time(), nullable=False),
    sa.Column('starts_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ends_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', lesson_status, server_default='confirmed', nullable=False),
    sa.Column('topic_covered', sa.Text(), nullable=True),
    sa.Column('homework', sa.Text(), nullable=True),
    sa.Column('reported_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('problem_window_ends_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('parent_price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('tutor_earning', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('earning_status', earning_status, server_default='pending', nullable=False),
    sa.Column('payable_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('payout_due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('payout_id', sa.Uuid(), nullable=True),
    sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], name=op.f('fk_lessons_booking_id_bookings')),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], name=op.f('fk_lessons_parent_id_users')),
    sa.ForeignKeyConstraint(['payout_id'], ['payouts.id'], name=op.f('fk_lessons_payout_id_payouts')),
    sa.ForeignKeyConstraint(['period_id'], ['booking_periods.id'], name=op.f('fk_lessons_period_id_booking_periods')),
    sa.ForeignKeyConstraint(['tutor_id'], ['users.id'], name=op.f('fk_lessons_tutor_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lessons')),
    sa.UniqueConstraint('booking_id', 'starts_at', name=op.f('uq_lessons_booking_id_starts_at'))
    )
    op.create_index(op.f('ix_lessons_parent_id'), 'lessons', ['parent_id'], unique=False)
    op.create_index(op.f('ix_lessons_payout_id'), 'lessons', ['payout_id'], unique=False)
    op.create_index(op.f('ix_lessons_period_id'), 'lessons', ['period_id'], unique=False)
    op.create_index(op.f('ix_lessons_tutor_id'), 'lessons', ['tutor_id'], unique=False)
    op.create_table('wallet_entries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('parent_id', sa.Uuid(), nullable=False),
    sa.Column('kind', wallet_entry_kind, nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('description', sa.String(), nullable=False),
    sa.Column('reference', sa.String(), nullable=True),
    sa.Column('period_id', sa.Uuid(), nullable=True),
    sa.Column('refund_id', sa.Uuid(), nullable=True),
    sa.Column('withdrawal_id', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['parent_id'], ['users.id'], name=op.f('fk_wallet_entries_parent_id_users')),
    sa.ForeignKeyConstraint(['period_id'], ['booking_periods.id'], name=op.f('fk_wallet_entries_period_id_booking_periods')),
    sa.ForeignKeyConstraint(['refund_id'], ['refunds.id'], name=op.f('fk_wallet_entries_refund_id_refunds')),
    sa.ForeignKeyConstraint(['withdrawal_id'], ['withdrawals.id'], name=op.f('fk_wallet_entries_withdrawal_id_withdrawals')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_wallet_entries')),
    sa.UniqueConstraint('reference', name=op.f('uq_wallet_entries_reference'))
    )
    op.create_index('ix_wallet_entries_parent_id_created_at', 'wallet_entries', ['parent_id', 'created_at'], unique=False)
    op.create_table('lesson_issues',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('lesson_id', sa.Uuid(), nullable=False),
    sa.Column('raised_by', sa.Uuid(), nullable=True),
    sa.Column('kind', issue_kind, nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('resolution', issue_resolution, nullable=True),
    sa.Column('resolution_note', sa.Text(), nullable=True),
    sa.Column('resolved_by', sa.Uuid(), nullable=True),
    sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['lesson_id'], ['lessons.id'], name=op.f('fk_lesson_issues_lesson_id_lessons')),
    sa.ForeignKeyConstraint(['raised_by'], ['users.id'], name=op.f('fk_lesson_issues_raised_by_users')),
    sa.ForeignKeyConstraint(['resolved_by'], ['users.id'], name=op.f('fk_lesson_issues_resolved_by_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_lesson_issues'))
    )
    op.create_index(op.f('ix_lesson_issues_lesson_id'), 'lesson_issues', ['lesson_id'], unique=False)

    op.execute("INSERT INTO platform_fees (id, parent_fee_rate, tutor_fee_rate, updated_at) VALUES (1, 0.10, 0.08, now())")


def _run_upgrade_of(filename: str) -> None:
    """Recreates an old table by running the migration that first created it."""
    path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.upgrade()


def downgrade() -> None:
    op.drop_table("lesson_issues")
    op.drop_table("wallet_entries")
    op.drop_table("lessons")
    op.drop_table("refunds")
    op.drop_table("booking_slots")
    op.drop_table("booking_periods")
    op.drop_table("tutor_offer_windows")
    op.drop_table("tutor_offer_subjects")
    op.drop_table("bookings")
    op.drop_table("withdrawals")
    op.drop_table("virtual_accounts")
    op.drop_table("tutor_offers")
    op.drop_table("tutor_bank_accounts")
    op.drop_table("platform_fees")
    op.drop_table("payouts")
    op.drop_table("notifications")
    for enum in NEW_ENUMS:
        enum.drop(op.get_bind(), checkfirst=True)

    op.drop_column("users", "photo_key")
    op.add_column("tutor_profiles", sa.Column("rate_per_session", sa.Numeric(precision=10, scale=2),
                                              server_default="0", nullable=False))
    op.alter_column("tutor_profiles", "rate_per_session", server_default=None)
    for filename in ("0002_tutor_subjects.py", "0003_schedules.py", "0004_sessions.py", "0005_billing.py"):
        _run_upgrade_of(filename)
