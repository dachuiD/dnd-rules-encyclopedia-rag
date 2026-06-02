from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


CORE_SOURCES = {"PHB", "DMG", "MM"}


class SearchScope(str, Enum):
    CORE = "core"
    FULL = "full"


@dataclass(frozen=True)
class Citation:
    source_id: str
    page: Optional[int] = None
    category: Optional[str] = None
    title: Optional[str] = None
    path: List[str] = field(default_factory=list)
    url: Optional[str] = None

    def label(self) -> str:
        bits = [bit for bit in [self.source_id, self.category, self.title] if bit]
        if self.page is not None:
            bits.append(f"p.{self.page}")
        return " / ".join(bits)


@dataclass(frozen=True)
class FiveEToolsRef:
    ref_type: str
    label: str
    raw: str
    parts: List[str] = field(default_factory=list)


@dataclass
class RuleDocument:
    id: str
    title_zh: str
    category: str
    source_id: str
    source_group: str
    search_scope: str
    knowledge_domain: str
    aliases: List[str]
    summary_text: str
    body_text: str
    structured_fields: Dict[str, Any]
    citation: Citation
    raw_ref: str
    raw_json: Dict[str, Any] = field(default_factory=dict)
    title_en: Optional[str] = None
    relations: List[FiveEToolsRef] = field(default_factory=list)
    semantic_tags: List[str] = field(default_factory=list)


@dataclass
class RuleChunk:
    id: str
    document_id: str
    chunk_level: str
    chunk_type: str
    title_path: List[str]
    text: str
    embedding_text: str
    display_text: str
    semantic_tags: List[str]
    citation: Citation
    source_id: str
    search_scope: str
    knowledge_domain: str
    category: str
    aliases: List[str] = field(default_factory=list)
    parent_chunk_id: Optional[str] = None


@dataclass
class EvidenceScore:
    dense_score: float = 0.0
    lexical_score: float = 0.0
    alias_score: float = 0.0
    title_score: float = 0.0
    source_score: float = 0.0
    structure_score: float = 0.0
    final_score: float = 0.0
    reasons: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    chunk: RuleChunk
    score: EvidenceScore

