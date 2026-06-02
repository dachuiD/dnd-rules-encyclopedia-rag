from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from .models import CORE_SOURCES, Citation, RuleDocument
from .text import entries_to_plain_text, extract_refs_from_entries


ENTITY_CATEGORIES = {
    "spells",
    "bestiary",
    "class",
    "classes",
    "items",
    "feats",
    "races",
    "backgrounds",
    "optionalfeatures",
}

RULE_CATEGORIES = {
    "actions",
    "conditions",
    "conditionsdiseases",
    "variantrules",
    "book",
}


class FiveEToolsNormalizer:
    def normalize_entry(self, entry: Dict[str, Any], category: str, raw_ref: str = "") -> RuleDocument:
        source_id = str(entry.get("source") or entry.get("src") or "UNKNOWN").upper()
        title_zh = str(entry.get("name") or entry.get("title") or "未命名条目")
        title_en = entry.get("ENG_name") or entry.get("eng_name") or entry.get("english")
        body_text = self._body_text(entry)
        aliases = self._aliases(title_zh, title_en, entry)
        source_group = "core" if source_id in CORE_SOURCES else "expansion"
        search_scope = "core" if source_group == "core" else "full"
        knowledge_domain = self._knowledge_domain(category)
        semantic_tags = self._semantic_tags(category, title_zh, body_text)
        doc_id = self._document_id(category, source_id, title_zh)

        citation = Citation(
            source_id=source_id,
            page=entry.get("page"),
            category=category,
            title=title_zh,
            path=[title_zh],
        )

        return RuleDocument(
            id=doc_id,
            title_zh=title_zh,
            title_en=str(title_en) if title_en else None,
            category=category,
            source_id=source_id,
            source_group=source_group,
            search_scope=search_scope,
            knowledge_domain=knowledge_domain,
            aliases=aliases,
            summary_text=body_text.split("\n", 1)[0] if body_text else title_zh,
            body_text=body_text,
            structured_fields=self._structured_fields(entry),
            citation=citation,
            raw_ref=raw_ref or f"{category}:{source_id}:{title_zh}",
            raw_json=entry,
            relations=extract_refs_from_entries(entry.get("entries", [])),
            semantic_tags=semantic_tags,
        )

    def _body_text(self, entry: Dict[str, Any]) -> str:
        parts: List[str] = []
        for key in ["entries", "entriesHigherLevel", "trait", "action", "reaction", "legendary", "variant"]:
            if key in entry:
                text = entries_to_plain_text(entry[key])
                if text:
                    parts.append(text)
        if not parts:
            for key in ["description", "text"]:
                if key in entry and entry[key]:
                    parts.append(entries_to_plain_text(entry[key]))
        return "\n".join(parts).strip()

    def _aliases(self, title_zh: str, title_en: Any, entry: Dict[str, Any]) -> List[str]:
        aliases: List[str] = [title_zh]
        if title_en:
            aliases.append(str(title_en))
        for key in ["alias", "aliases", "otherSources"]:
            value = entry.get(key)
            if isinstance(value, str):
                aliases.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        aliases.append(item)
        return sorted({alias.strip() for alias in aliases if alias and alias.strip()})

    def _knowledge_domain(self, category: str) -> str:
        if category in RULE_CATEGORIES:
            return "rules"
        if category in ENTITY_CATEGORIES:
            return "entity"
        if category.startswith("adventure"):
            return "adventure"
        if category in {"names", "encounters", "recipes", "roll20-module"}:
            return "utility"
        return "lore"

    def _semantic_tags(self, category: str, title: str, body: str) -> List[str]:
        corpus = f"{category} {title} {body}"
        tags: List[str] = []
        tag_keywords = {
            "combat": ["攻击", "伤害", "护甲", "战斗", "借机", "反应"],
            "condition": ["状态", "隐形", "目盲", "倒地", "束缚", "中毒"],
            "spellcasting": ["法术", "施法", "专注", "法术位", "环阶"],
            "action_economy": ["动作", "附赠动作", "反应", "移动"],
            "saving_throw": ["豁免", "检定"],
        }
        for tag, keywords in tag_keywords.items():
            if any(keyword in corpus for keyword in keywords):
                tags.append(tag)
        if category in {"spells"}:
            tags.append("spell")
        if category in {"bestiary"}:
            tags.append("monster")
        return sorted(set(tags))

    def _structured_fields(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        excluded = {"entries", "entriesHigherLevel", "trait", "action", "reaction", "legendary", "variant"}
        return {key: value for key, value in entry.items() if key not in excluded}

    def _document_id(self, category: str, source_id: str, title: str) -> str:
        raw = json.dumps([category, source_id, title], ensure_ascii=False)
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10]
        safe_title = "".join(ch if ch.isalnum() else "-" for ch in title.lower()).strip("-")
        return f"{category}.{source_id.lower()}.{safe_title}.{digest}"

