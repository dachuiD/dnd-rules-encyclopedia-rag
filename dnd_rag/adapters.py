from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .models import RuleDocument
from .normalize import FiveEToolsNormalizer


ENTRY_KEYS = {
    "action": "actions",
    "condition": "conditions",
    "disease": "conditions",
    "status": "conditionsdiseases",
    "spell": "spells",
    "monster": "bestiary",
    "class": "class",
    "item": "items",
    "feat": "feats",
    "race": "races",
    "background": "backgrounds",
    "optionalfeature": "optionalfeatures",
    "variantrule": "variantrules",
    "data": "book",
}

EXCLUDED_PATH_PARTS = {"roll20-module", "adventure"}
EXCLUDED_FILES = {"names.json", "encounters.json", "recipes.json", "roll20-tables.json", "changelog.json"}


class FiveEToolsCnAdapter:
    def __init__(self, data_dir: Path, normalizer: Optional[FiveEToolsNormalizer] = None) -> None:
        self.data_dir = data_dir
        self.normalizer = normalizer or FiveEToolsNormalizer()

    @classmethod
    def sample(cls) -> "FiveEToolsCnAdapter":
        return cls(Path(__file__).resolve().parent.parent / "sample_data" / "5etools")

    def load_documents(self) -> List[RuleDocument]:
        documents: List[RuleDocument] = []
        for path in self._iter_json_files():
            documents.extend(self._load_file(path))
        return [doc for doc in documents if doc.knowledge_domain in {"rules", "entity", "lore"}]

    def _iter_json_files(self) -> Iterable[Path]:
        if self.data_dir.is_file():
            yield self.data_dir
            return
        for path in sorted(self.data_dir.rglob("*.json")):
            rel_parts = set(path.relative_to(self.data_dir).parts)
            if rel_parts & EXCLUDED_PATH_PARTS:
                continue
            if path.name in EXCLUDED_FILES or path.name.startswith("fluff-"):
                continue
            yield path

    def _load_file(self, path: Path) -> List[RuleDocument]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        docs: List[RuleDocument] = []
        for key, category in ENTRY_KEYS.items():
            entries = payload.get(key)
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if isinstance(entry, dict):
                    docs.append(self.normalizer.normalize_entry(entry, category, raw_ref=str(path)))
        return docs
