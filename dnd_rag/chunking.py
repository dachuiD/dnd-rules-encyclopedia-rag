from __future__ import annotations

import hashlib
from typing import Iterable, List

from .models import Citation, RuleChunk, RuleDocument
from .text import entries_to_plain_text, iter_entry_sections


DOUBLE_LAYER_CATEGORIES = {"actions", "conditions", "conditionsdiseases", "spells", "variantrules", "book"}


def build_chunks(doc: RuleDocument) -> List[RuleChunk]:
    chunks: List[RuleChunk] = []
    parent_type = _chunk_type(doc)
    parent = _make_chunk(
        doc=doc,
        chunk_level="parent",
        chunk_type=parent_type,
        title_path=[doc.title_zh],
        text=doc.body_text or doc.summary_text,
        parent_chunk_id=None,
        suffix="parent",
    )
    chunks.append(parent)

    if doc.category in DOUBLE_LAYER_CATEGORIES:
        children = _child_chunks(doc, parent.id)
        chunks.extend(children)
    elif doc.category == "bestiary":
        chunks.extend(_monster_chunks(doc, parent.id))
    else:
        chunks.extend(_generic_children(doc, parent.id))

    return [chunk for chunk in chunks if chunk.text.strip()]


def _child_chunks(doc: RuleDocument, parent_id: str) -> List[RuleChunk]:
    entries = []
    raw = doc.raw_json
    for key in ["entries", "entriesHigherLevel"]:
        if key in raw:
            for path, text in iter_entry_sections(raw[key]):
                entries.append((path, text))
    chunks: List[RuleChunk] = []
    for idx, (path, text) in enumerate(entries):
        title_path = [doc.title_zh] + path
        chunks.append(
            _make_chunk(
                doc=doc,
                chunk_level="child",
                chunk_type=_chunk_type(doc, path),
                title_path=title_path,
                text=text,
                parent_chunk_id=parent_id,
                suffix=f"child-{idx}",
            )
        )
    return chunks


def _monster_chunks(doc: RuleDocument, parent_id: str) -> List[RuleChunk]:
    chunks: List[RuleChunk] = []
    for key, chunk_type in [("trait", "feature"), ("action", "stat_block"), ("reaction", "stat_block"), ("legendary", "stat_block")]:
        if key not in doc.raw_json:
            continue
        for idx, (path, text) in enumerate(iter_entry_sections(doc.raw_json[key])):
            chunks.append(
                _make_chunk(
                    doc=doc,
                    chunk_level="child",
                    chunk_type=chunk_type,
                    title_path=[doc.title_zh, key] + path,
                    text=text,
                    parent_chunk_id=parent_id,
                    suffix=f"{key}-{idx}",
                )
            )
    return chunks


def _generic_children(doc: RuleDocument, parent_id: str) -> List[RuleChunk]:
    if len(doc.body_text) <= 600:
        return []
    paragraphs = [part.strip() for part in doc.body_text.split("\n") if part.strip()]
    return [
        _make_chunk(
            doc=doc,
            chunk_level="child",
            chunk_type=_chunk_type(doc),
            title_path=[doc.title_zh, f"段落 {idx + 1}"],
            text=text,
            parent_chunk_id=parent_id,
            suffix=f"para-{idx}",
        )
        for idx, text in enumerate(paragraphs)
    ]


def _make_chunk(
    doc: RuleDocument,
    chunk_level: str,
    chunk_type: str,
    title_path: List[str],
    text: str,
    parent_chunk_id: str | None,
    suffix: str,
) -> RuleChunk:
    display_text = _clip(text, 420)
    embedding_text = "\n".join(
        [
            f"分类：{doc.category}",
            f"条目：{doc.title_zh}",
            f"英文名：{doc.title_en or ''}",
            f"来源：{doc.source_id}",
            f"标题路径：{' / '.join(title_path)}",
            f"标签：{'，'.join(doc.semantic_tags)}",
            f"正文：{text}",
        ]
    ).strip()
    citation = Citation(
        source_id=doc.source_id,
        page=doc.citation.page,
        category=doc.category,
        title=doc.title_zh,
        path=title_path,
        url=doc.citation.url,
    )
    return RuleChunk(
        id=_chunk_id(doc.id, suffix, text),
        document_id=doc.id,
        parent_chunk_id=parent_chunk_id,
        chunk_level=chunk_level,
        chunk_type=chunk_type,
        title_path=title_path,
        text=text,
        embedding_text=embedding_text,
        display_text=display_text,
        semantic_tags=doc.semantic_tags,
        citation=citation,
        source_id=doc.source_id,
        search_scope=doc.search_scope,
        knowledge_domain=doc.knowledge_domain,
        category=doc.category,
        aliases=doc.aliases,
    )


def _chunk_type(doc: RuleDocument, path: Iterable[str] = ()) -> str:
    if doc.category == "spells":
        return "spell_description"
    if doc.category in {"actions", "conditions", "conditionsdiseases", "variantrules", "book"}:
        return "rule"
    if doc.category in {"class", "classes", "feats", "optionalfeatures"}:
        return "feature"
    if doc.category == "bestiary":
        return "stat_block"
    if doc.knowledge_domain == "lore":
        return "fluff"
    return "definition"


def _chunk_id(document_id: str, suffix: str, text: str) -> str:
    digest = hashlib.sha1(f"{document_id}:{suffix}:{text}".encode("utf-8")).hexdigest()[:10]
    return f"{document_id}.chunk.{suffix}.{digest}"


def _clip(text: str, limit: int) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "…"

