from sqlalchemy.orm import Session

from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.policies import index_policy


def main() -> None:
    engine = create_database_engine(Settings())
    try:
        with Session(engine) as session, session.begin():
            count = index_policy(session)
        print(f"Indexed {count} policy sections")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
