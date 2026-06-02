from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .models import RuleChunk
from .providers import EmbeddingProvider

@dataclass(frozen=True)
class EmbeddingIndexRow:
    chunk_id: str
    document_id: str
    embedding_text_hash: str
    model: str
    dimensions: int
    embedding: List[float]


@dataclass(frozen=True)
class EmbeddingIndexBuildReport:
    requested_chunks: int
    cache_hits: int
    embedded_rows: int
    total_rows: int
    model: str
    dimensions: int
    out_path: str


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_embedding_index(path: Path, rows: Iterable[EmbeddingIndexRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")


def load_embedding_index(path: Path) -> List[EmbeddingIndexRow]:
    if not path.exists():
        return []
    rows: List[EmbeddingIndexRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        rows.append(
            EmbeddingIndexRow(
                chunk_id=data["chunk_id"],
                document_id=data["document_id"],
                embedding_text_hash=data["embedding_text_hash"],
                model=data["model"],
                dimensions=int(data["dimensions"]),
                embedding=[float(value) for value in data["embedding"]],
            )
        )
    return rows


def filter_fresh_rows(
    rows: Iterable[EmbeddingIndexRow],
    expected_hash_by_chunk: Dict[str, str],
    model: str,
    dimensions: int,
) -> Dict[str, EmbeddingIndexRow]:
    fresh: Dict[str, EmbeddingIndexRow] = {}
    for row in rows:
        if row.model != model:
            continue
        if row.dimensions != dimensions:
            continue
        if expected_hash_by_chunk.get(row.chunk_id) != row.embedding_text_hash:
            continue
        fresh[row.chunk_id] = row
    return fresh


def build_embedding_index(
    chunks: Sequence[RuleChunk],
    provider: EmbeddingProvider,
    out_path: Path,
    limit: int = 300,
    batch_size: int = 32,
    model: str = "text-embedding-v4",
    dimensions: int = 1024,
) -> EmbeddingIndexBuildReport:
    selected = list(chunks[:limit])
    expected_hashes = {chunk.id: text_hash(chunk.embedding_text) for chunk in selected}
    cached_rows = filter_fresh_rows(load_embedding_index(out_path), expected_hashes, model=model, dimensions=dimensions)
    rows_by_chunk = dict(cached_rows)
    missing = [chunk for chunk in selected if chunk.id not in cached_rows]
    embedded_rows = 0

    for start in range(0, len(missing), batch_size):
        batch = missing[start : start + batch_size]
        vectors = provider.embed([chunk.embedding_text for chunk in batch])
        for chunk, vector in zip(batch, vectors):
            rows_by_chunk[chunk.id] = EmbeddingIndexRow(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                embedding_text_hash=expected_hashes[chunk.id],
                model=model,
                dimensions=dimensions,
                embedding=[float(value) for value in vector],
            )
            embedded_rows += 1

    ordered_rows = [rows_by_chunk[chunk.id] for chunk in selected if chunk.id in rows_by_chunk]
    write_embedding_index(out_path, ordered_rows)
    return EmbeddingIndexBuildReport(
        requested_chunks=len(selected),
        cache_hits=len(cached_rows),
        embedded_rows=embedded_rows,
        total_rows=len(ordered_rows),
        model=model,
        dimensions=dimensions,
        out_path=str(out_path),
    )
