from __future__ import annotations

import hashlib
import json
import math
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
    segment_count: int = 1


@dataclass(frozen=True)
class EmbeddingIndexBuildReport:
    requested_chunks: int
    cache_hits: int
    embedded_rows: int
    embedded_segments: int
    segmented_chunks: int
    fallback_batches: int
    total_rows: int
    model: str
    dimensions: int
    max_segment_chars: int
    out_path: str


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_embedding_index(path: Path, rows: Iterable[EmbeddingIndexRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")
    tmp_path.replace(path)


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
                segment_count=int(data.get("segment_count", 1)),
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
    batch_size: int = 20,
    model: str = "text-embedding-v4",
    dimensions: int = 1024,
    max_segment_chars: int = 4000,
    checkpoint_every_chunks: int = 500,
) -> EmbeddingIndexBuildReport:
    selected = list(chunks if limit <= 0 else chunks[:limit])
    expected_hashes = {chunk.id: text_hash(chunk.embedding_text) for chunk in selected}
    cached_rows = filter_fresh_rows(load_embedding_index(out_path), expected_hashes, model=model, dimensions=dimensions)
    rows_by_chunk = dict(cached_rows)
    missing = [chunk for chunk in selected if chunk.id not in cached_rows]
    embedded_rows = 0
    embedded_segments = 0
    segmented_chunks = 0
    fallback_batches = 0
    chunks_since_checkpoint = 0
    pending: List[tuple[RuleChunk, str]] = []

    for chunk in missing:
        segments = split_embedding_text(chunk.embedding_text, max_segment_chars=max_segment_chars)
        if len(segments) > 1:
            segmented_chunks += 1
        for segment in segments:
            pending.append((chunk, segment))

    vectors_by_chunk: Dict[str, List[List[float]]] = {chunk.id: [] for chunk in missing}
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        vectors, fallbacks = _embed_with_fallback(provider, [segment for _, segment in batch])
        fallback_batches += fallbacks
        for (chunk, _segment), vector in zip(batch, vectors):
            vectors_by_chunk[chunk.id].append([float(value) for value in vector])
            embedded_segments += 1

        completed_chunks = [
            chunk
            for chunk in missing
            if chunk.id not in rows_by_chunk and len(vectors_by_chunk[chunk.id]) == len(split_embedding_text(chunk.embedding_text, max_segment_chars=max_segment_chars))
        ]
        for chunk in completed_chunks:
            vectors = vectors_by_chunk[chunk.id]
            rows_by_chunk[chunk.id] = EmbeddingIndexRow(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                embedding_text_hash=expected_hashes[chunk.id],
                model=model,
                dimensions=dimensions,
                embedding=_average_vectors(vectors),
                segment_count=len(vectors),
            )
        embedded_rows += len(completed_chunks)
        chunks_since_checkpoint += len(completed_chunks)
        if completed_chunks and chunks_since_checkpoint >= checkpoint_every_chunks:
            write_embedding_index(out_path, [rows_by_chunk[chunk.id] for chunk in selected if chunk.id in rows_by_chunk])
            chunks_since_checkpoint = 0

    for chunk in missing:
        if chunk.id in rows_by_chunk:
            continue
        vectors = vectors_by_chunk[chunk.id]
        if not vectors:
            continue
        rows_by_chunk[chunk.id] = EmbeddingIndexRow(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            embedding_text_hash=expected_hashes[chunk.id],
            model=model,
            dimensions=dimensions,
            embedding=_average_vectors(vectors),
            segment_count=len(vectors),
        )
        embedded_rows += 1

    ordered_rows = [rows_by_chunk[chunk.id] for chunk in selected if chunk.id in rows_by_chunk]
    write_embedding_index(out_path, ordered_rows)
    return EmbeddingIndexBuildReport(
        requested_chunks=len(selected),
        cache_hits=len(cached_rows),
        embedded_rows=embedded_rows,
        embedded_segments=embedded_segments,
        segmented_chunks=segmented_chunks,
        fallback_batches=fallback_batches,
        total_rows=len(ordered_rows),
        model=model,
        dimensions=dimensions,
        max_segment_chars=max_segment_chars,
        out_path=str(out_path),
    )


def _embed_with_fallback(provider: EmbeddingProvider, texts: Sequence[str]) -> tuple[List[List[float]], int]:
    if not texts:
        return [], 0
    try:
        return provider.embed(list(texts)), 0
    except Exception:
        if len(texts) == 1:
            raise
        midpoint = len(texts) // 2
        left, left_fallbacks = _embed_with_fallback(provider, texts[:midpoint])
        right, right_fallbacks = _embed_with_fallback(provider, texts[midpoint:])
        return left + right, left_fallbacks + right_fallbacks + 1


def split_embedding_text(text: str, max_segment_chars: int = 4000) -> List[str]:
    clean = text.strip()
    if not clean:
        return [""]
    if len(clean) <= max_segment_chars:
        return [clean]

    paragraphs = [part.strip() for part in clean.split("\n\n") if part.strip()]
    segments: List[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_segment_chars:
            if current:
                segments.append(current)
                current = ""
            segments.extend(_hard_split(paragraph, max_segment_chars))
            continue
        candidate = paragraph if not current else current + "\n\n" + paragraph
        if len(candidate) <= max_segment_chars:
            current = candidate
        else:
            if current:
                segments.append(current)
            current = paragraph
    if current:
        segments.append(current)
    return segments or [clean]


def _hard_split(text: str, max_segment_chars: int) -> List[str]:
    return [text[start : start + max_segment_chars] for start in range(0, len(text), max_segment_chars)]


def _average_vectors(vectors: Sequence[Sequence[float]]) -> List[float]:
    if not vectors:
        return []
    size = min(len(vector) for vector in vectors)
    if size == 0:
        return []
    averaged = [sum(vector[index] for vector in vectors) / len(vectors) for index in range(size)]
    norm = math.sqrt(sum(value * value for value in averaged))
    if norm == 0:
        return averaged
    return [value / norm for value in averaged]
