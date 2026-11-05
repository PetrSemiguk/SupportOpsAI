from alembic import context
from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.retail import RetailBase


def run_migrations() -> None:
    settings = Settings()
    if context.is_offline_mode():
        context.configure(
            url=settings.database_url.get_secret_value(),
            target_metadata=RetailBase.metadata,
            literal_binds=True,
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    engine = create_database_engine(settings)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=RetailBase.metadata)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
