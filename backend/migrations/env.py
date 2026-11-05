from alembic import context
from supportops.config import Settings
from supportops.database import create_database_engine


def run_migrations() -> None:
    settings = Settings()
    if context.is_offline_mode():
        context.configure(
            url=settings.database_url.get_secret_value(),
            target_metadata=None,
            literal_binds=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = create_database_engine(settings)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
