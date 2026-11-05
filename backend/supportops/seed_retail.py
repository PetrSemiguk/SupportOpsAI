import argparse
import json
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from urllib.request import urlopen

from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from supportops.config import Settings
from supportops.database import create_database_engine
from supportops.retail import Customer, Order, OrderStatus

REVISION = "033bf082f48e4a3c6a1256208e93cf2ce9c3bb6f"
ROOT = f"https://raw.githubusercontent.com/sierra-research/tau2-bench/{REVISION}/"
RETAIL = "data/tau2/domains/retail/"
SOURCE_FILES = {
    RETAIL + "db.json": "413a65160adbdb5fde0ffc0015c49b6d70250b10c18128de169b597af7766765",
    RETAIL + "policy.md": "2c9652afbce57d6e087768d37cda64d31c53d50b3e3225cfdb791bac66466467",
    RETAIL + "tasks.json": "8e03ebce7901bd6218e7a7dc3105faa9324091a68058f7fe61c65262868812e8",
    "LICENSE": "e67c5aa0074dfcaefd3c3a1aedb94cb539234aecd15d5a972574e3200e6252fe",
}


class SourceItem(BaseModel):
    item_id: str
    name: str
    price: Decimal


class SourceFulfillment(BaseModel):
    tracking_id: list[str]


class SourcePayment(BaseModel):
    transaction_type: str
    payment_method_id: str


class SourceOrder(BaseModel):
    order_id: str
    user_id: str
    status: OrderStatus
    items: list[SourceItem]
    fulfillments: list[SourceFulfillment]
    payment_history: list[SourcePayment]


class SourceStore(BaseModel):
    orders: dict[str, SourceOrder]


@dataclass(frozen=True)
class SeedResult:
    customers: int
    selected_orders: int
    inserted_orders: int


def read_source(directory: Path, download: bool) -> SourceStore:
    for source_path, digest in SOURCE_FILES.items():
        destination = directory / Path(source_path).name
        if download and not destination.exists():
            with urlopen(ROOT + source_path, timeout=30) as response:
                data = response.read()
            if sha256(data).hexdigest() != digest:
                raise ValueError(f"Unexpected checksum for {destination.name}")
            directory.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
        if sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Unexpected checksum for {destination.name}")
    return SourceStore.model_validate_json((directory / "db.json").read_bytes())


def seed_orders(session: Session, source: SourceStore) -> SeedResult:
    counts: Counter[str] = Counter()
    selection: list[SourceOrder] = []
    for order in sorted(source.orders.values(), key=lambda record: record.order_id):
        if counts[order.status] < 6:
            selection.append(order)
            counts[order.status] += 1

    aliases = {
        user_id: f"demo-{number:03d}"
        for number, user_id in enumerate(sorted({order.user_id for order in selection}), start=1)
    }
    if aliases:
        session.execute(
            insert(Customer)
            .values([{"id": alias} for alias in aliases.values()])
            .on_conflict_do_nothing(index_elements=[Customer.id])
        )

    rows = [
        {
            "id": order.order_id,
            "customer_id": aliases[order.user_id],
            "status": order.status,
            "items": [
                {"id": item.item_id, "name": item.name, "price": str(item.price)}
                for item in order.items
            ],
            "tracking_ids": [
                tracking
                for fulfillment in order.fulfillments
                for tracking in fulfillment.tracking_id
            ],
            "payment_sources": sorted(
                {
                    payment.payment_method_id.rsplit("_", 1)[0]
                    for payment in order.payment_history
                    if payment.transaction_type == "payment"
                }
            ),
        }
        for order in selection
    ]
    inserted = (
        session.scalars(
            insert(Order)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[Order.id])
            .returning(Order.id)
        ).all()
        if rows
        else []
    )
    return SeedResult(len(aliases), len(rows), len(inserted))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed a bounded retail demo from pinned τ-bench data"
    )
    parser.add_argument("--directory", type=Path, default=Path("data/raw/tau-retail"))
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    source = read_source(args.directory, args.download)
    engine = create_database_engine(Settings())
    try:
        with Session(engine) as session, session.begin():
            result = seed_orders(session, source)
        print(json.dumps(result.__dict__))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
