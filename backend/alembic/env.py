from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add the parent directory to sys.path so we can import our models
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.models.models import Base
from app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

def get_url():
    return settings.database_url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def _drop_stale_alembic_type(connection, version_table: str = "alembic_version") -> None:
    """Remove lingering composite types that block version table creation."""

    if connection.dialect.name != "postgresql":
        return

    schema = connection.exec_driver_sql("SELECT current_schema()").scalar()

    table_exists = connection.exec_driver_sql(
        "SELECT to_regclass(%(regclass)s)",
        {"regclass": f"{schema}.{version_table}"},
    ).scalar()

    if table_exists:
        return

    type_exists = connection.exec_driver_sql(
        """
        SELECT 1
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE t.typname = %(type_name)s
          AND n.nspname = %(schema)s
        LIMIT 1
        """,
        {"type_name": version_table, "schema": schema},
    ).scalar()

    if type_exists:
        connection.exec_driver_sql(
            f'DROP TYPE IF EXISTS "{schema}"."{version_table}" CASCADE'
        )


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connection = config.attributes.get("connection")
    if connection is not None:
        _drop_stale_alembic_type(connection)
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _drop_stale_alembic_type(connection)
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()