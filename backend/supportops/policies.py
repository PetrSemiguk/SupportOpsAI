import re
from hashlib import blake2b, sha256
from pathlib import Path
from typing import Annotated

from langchain_core.embeddings import Embeddings
from pgvector.sqlalchemy import VECTOR
from pydantic import BaseModel, Field
from sqlalchemy import Float, String, Text, delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Mapped, Session, mapped_column

from supportops.foundry import VECTOR_DIMENSIONS, FoundryEmbeddings
from supportops.retail import RetailBase

DIMENSIONS = VECTOR_DIMENSIONS
POLICY_FILE = Path("data/policies/retail.md")
OFFLINE_MODEL = "offline-token-hash-v1"
MIN_SIMILARITY = 0.22
SECTION = re.compile(r"^## (.+?) \[([a-z][a-z0-9-]*)\] *$", re.MULTILINE)
WORDS = re.compile(r"[a-z0-9]+")
STOP_WORDS = frozenset(
    "a an and are as at be by can do for from have how i in is it me my of on or so "
    "that the their this to was were what when where which who will with would you your".split()
)
ALIASES = {
    "cancellation": "cancel",
    "cancelled": "cancel",
    "canceled": "cancel",
    "delivery": "delivered",
    "refunds": "refund",
    "returns": "return",
    "repayment": "refund",
    "tracking": "track",
}


class PolicySection(RetailBase):
    __tablename__ = "policy_sections"

    document: Mapped[str] = mapped_column(String(200), primary_key=True)
    section_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    model_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    revision: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float]] = mapped_column(VECTOR(DIMENSIONS))


class PolicyExcerpt(BaseModel):
    citation: str
    document: str
    revision: str
    title: str
    content: str
    similarity: Annotated[float, Field(ge=0, le=1)]


class PolicySearchResult(BaseModel):
    embedding_model: str
    excerpts: list[PolicyExcerpt]


def terms(text: str) -> set[str]:
    return {
        ALIASES.get(word, word) for word in WORDS.findall(text.lower()) if word not in STOP_WORDS
    }


class OfflinePolicyEmbeddings(Embeddings):
    """Deterministic lexical vectors for the local demo and its integration tests."""

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * DIMENSIONS
        for term in terms(text):
            digest = blake2b(term.encode(), digest_size=3).digest()
            index = int.from_bytes(digest[:2], "big") % DIMENSIONS
            vector[index] += 1.0 if digest[2] % 2 else -1.0
        return vector

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]


def index_policy(
    session: Session,
    path: Path = POLICY_FILE,
    hosted: FoundryEmbeddings | None = None,
) -> int:
    content = path.read_text(encoding="utf-8")
    # Hash normalized text so checkout line endings do not affect citations.
    revision = sha256(content.encode()).hexdigest()
    sections = list(SECTION.finditer(content))
    if not sections:
        raise ValueError("Policy has no titled sections with citation identifiers")
    document = path.as_posix()
    model_id = hosted.model_id if hosted else OFFLINE_MODEL
    rows = []
    for index, section in enumerate(sections):
        end = sections[index + 1].start() if index + 1 < len(sections) else len(content)
        excerpt = content[section.end() : end].strip()
        if not excerpt:
            raise ValueError(f"Empty policy section {section[2]}")
        rows.append(
            {
                "document": document,
                "section_id": section[2],
                "model_id": model_id,
                "title": section[1],
                "content": excerpt,
                "revision": revision,
            }
        )
    if len({row["section_id"] for row in rows}) != len(rows):
        raise ValueError("Policy section identifiers must be unique")
    embeddings = (hosted or OfflinePolicyEmbeddings()).embed_documents(
        [f"{row['title']} {row['content']}" for row in rows]
    )
    statement = insert(PolicySection).values(
        [{**row, "embedding": embedding} for row, embedding in zip(rows, embeddings, strict=True)]
    )
    session.execute(
        statement.on_conflict_do_update(
            index_elements=[
                PolicySection.document,
                PolicySection.section_id,
                PolicySection.model_id,
            ],
            set_={
                key: getattr(statement.excluded, key)
                for key in ("title", "content", "revision", "embedding")
            },
        )
    )
    session.execute(
        delete(PolicySection).where(
            PolicySection.document == document,
            PolicySection.model_id == model_id,
            PolicySection.section_id.not_in([row["section_id"] for row in rows]),
        )
    )
    return len(rows)


def search_policies(
    session: Session,
    query: str,
    limit: int = 3,
    hosted: FoundryEmbeddings | None = None,
) -> PolicySearchResult:
    model_id = hosted.model_id if hosted else OFFLINE_MODEL
    result = PolicySearchResult(embedding_model=model_id, excerpts=[])
    if not query.strip():
        return result
    if (
        hosted
        and session.scalar(
            select(PolicySection.section_id)
            .where(
                PolicySection.model_id == model_id,
            )
            .limit(1)
        )
        is None
    ):
        # Require a deliberate index build before incurring a hosted query.
        return result
    embedding = (hosted or OfflinePolicyEmbeddings()).embed_query(query)
    if not any(embedding):
        return result
    distance = PolicySection.embedding.op("<=>", return_type=Float)(embedding)
    statement = (
        select(PolicySection, distance)
        .where(PolicySection.model_id == model_id, distance <= 1 - MIN_SIMILARITY)
        .order_by(distance, PolicySection.document, PolicySection.section_id)
    )
    query_terms = terms(query)
    for section, score_distance in session.execute(statement):
        if not hosted and not query_terms.intersection(terms(f"{section.title} {section.content}")):
            # An accidental hash collision is insufficient evidence.
            continue
        result.excerpts.append(
            PolicyExcerpt(
                citation=f"{section.document}#{section.section_id}",
                document=section.document,
                revision=section.revision,
                title=section.title,
                content=section.content,
                similarity=min(1.0, 1.0 - score_distance),
            )
        )
        if len(result.excerpts) >= limit:
            break
    return result
