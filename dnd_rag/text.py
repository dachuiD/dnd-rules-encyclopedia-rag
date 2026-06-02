from __future__ import annotations

import re
from typing import Any, Iterable, List, Tuple

from .models import FiveEToolsRef


TAG_RE = re.compile(r"\{@([a-zA-Z]+)\s+([^{}]+?)\}")
WHITESPACE_RE = re.compile(r"\s+")


def _label_from_tag_payload(payload: str) -> Tuple[str, List[str]]:
    parts = payload.split("|")
    label = parts[0].strip()
    return label, [part.strip() for part in parts if part.strip()]


def clean_5etools_text(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        label, _ = _label_from_tag_payload(match.group(2))
        return label

    cleaned = TAG_RE.sub(replace, str(text))
    cleaned = cleaned.replace("\u200b", "")
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def extract_5etools_refs(text: str) -> List[FiveEToolsRef]:
    refs: List[FiveEToolsRef] = []
    for match in TAG_RE.finditer(str(text)):
        label, parts = _label_from_tag_payload(match.group(2))
        refs.append(
            FiveEToolsRef(
                ref_type=match.group(1),
                label=label,
                raw=match.group(0),
                parts=parts,
            )
        )
    return refs


def entries_to_plain_text(entries: Any) -> str:
    lines: List[str] = []

    def walk(node: Any, path: List[str]) -> None:
        if node is None:
            return
        if isinstance(node, str):
            text = clean_5etools_text(node)
            if text:
                if path:
                    lines.append(f"{' / '.join(path)}：{text}")
                else:
                    lines.append(text)
            return
        if isinstance(node, list):
            for item in node:
                walk(item, path)
            return
        if isinstance(node, dict):
            name = clean_5etools_text(node.get("name", ""))
            next_path = path + [name] if name else path
            for key in ["entries", "items", "rows", "caption"]:
                if key in node:
                    walk(node[key], next_path)
            return
        lines.append(clean_5etools_text(str(node)))

    walk(entries, [])
    return "\n".join(line for line in lines if line)


def extract_refs_from_entries(entries: Any) -> List[FiveEToolsRef]:
    refs: List[FiveEToolsRef] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            refs.extend(extract_5etools_refs(node))
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for value in node.values():
                walk(value)

    walk(entries)
    return refs


def iter_entry_sections(entries: Any) -> Iterable[Tuple[List[str], str]]:
    def walk(node: Any, path: List[str]) -> Iterable[Tuple[List[str], str]]:
        if node is None:
            return
        if isinstance(node, str):
            text = clean_5etools_text(node)
            if text:
                yield path, text
            return
        if isinstance(node, list):
            for item in node:
                yield from walk(item, path)
            return
        if isinstance(node, dict):
            name = clean_5etools_text(node.get("name", ""))
            next_path = path + [name] if name else path
            yielded = False
            for key in ["entries", "items", "rows"]:
                if key in node:
                    yielded = True
                    yield from walk(node[key], next_path)
            if not yielded and name:
                yield path, name

    yield from walk(entries, [])

