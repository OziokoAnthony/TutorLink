"""No two parents share an account number

Each parent's dedicated account number (spec 1 R3.1) is theirs alone; the database enforces it
rather than trusting the payment provider.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-08
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint("uq_virtual_accounts_account_number", "virtual_accounts", ["account_number"])


def downgrade() -> None:
    op.drop_constraint("uq_virtual_accounts_account_number", "virtual_accounts", type_="unique")
