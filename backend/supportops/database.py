from sqlalchemy import Engine, create_engine, text

from supportops.config import Settings


def create_database_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )


def check_database(engine: Engine) -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        # Readiness includes schema initialization and the retrieval extension.
        connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        connection.execute(text("SELECT '[1,2]'::vector"))
