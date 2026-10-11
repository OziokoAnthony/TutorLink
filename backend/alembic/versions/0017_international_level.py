"""International high school level

Adds 'international' to the `education_level` enum: high school in an international curriculum
(British IGCSE and A-Level, IB, American). Offers, bookings, job posts and exam questions all share
the enum, so they all accept it.

Revision ID: 0017
Revises: 0016
Create Date: 2026-10-09
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_VALUES = "'primary', 'junior_secondary', 'senior_secondary'"


def upgrade() -> None:
    op.execute("ALTER TYPE education_level ADD VALUE IF NOT EXISTS 'international'")


def downgrade() -> None:
    """PostgreSQL can't drop an enum value, so the type is rebuilt without it. Fails while any row
    still uses 'international'."""
    op.execute("ALTER TYPE education_level RENAME TO education_level_old")
    op.execute(f"CREATE TYPE education_level AS ENUM ({OLD_VALUES})")
    op.execute("""
        DO $$
        DECLARE col record;
        BEGIN
            FOR col IN
                SELECT table_name, column_name FROM information_schema.columns
                WHERE table_schema = current_schema() AND udt_name = 'education_level_old'
            LOOP
                EXECUTE format('ALTER TABLE %I ALTER COLUMN %I TYPE education_level USING %I::text::education_level',
                               col.table_name, col.column_name, col.column_name);
            END LOOP;
        END $$
    """)
    op.execute("DROP TYPE education_level_old")
