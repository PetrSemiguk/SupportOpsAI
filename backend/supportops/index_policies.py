import argparse

from sqlalchemy.orm import Session

from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.foundry import FoundryClient, FoundryEmbeddings
from supportops.policies import index_policy


def main() -> None:
    parser = argparse.ArgumentParser(description="Index the versioned retail policies")
    parser.add_argument(
        "--foundry", action="store_true", help="Explicitly use configured hosted embeddings"
    )
    args = parser.parse_args()
    settings = Settings()
    hosted = None
    if args.foundry:
        if not settings.foundry_enabled or not settings.foundry_embedding_deployment:
            parser.error("Enable Foundry and configure an embedding deployment first")
        hosted = FoundryEmbeddings(FoundryClient(settings), settings.foundry_embedding_deployment)
    engine = create_database_engine(settings)
    try:
        with Session(engine) as session, session.begin():
            count = index_policy(session, hosted=hosted)
        print(f"Indexed {count} policy sections")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
