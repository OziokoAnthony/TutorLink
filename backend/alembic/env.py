from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from app.core.config import settings

# Import every domain's models so SQLModel.metadata knows about all tables.
from app.domains.auth import models as auth_models  # noqa: F401
from app.domains.billing import models as billing_models  # noqa: F401
from app.domains.reviews import models as reviews_models  # noqa: F401
from app.domains.schedules import models as schedules_models  # noqa: F401
from app.domains.sessions import models as sessions_models  # noqa: F401
from app.domains.tutors import models as tutors_models  # noqa: F401
from app.domains.webhooks import models as webhooks_models  # noqa: F401

config = context.config
# A URL set programmatically (e.g. by the test suite) wins over the environment.
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.ALEMBIC_DATABASE_URL or settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
