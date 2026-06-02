from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .adapters import EXCLUDED_FILES, EXCLUDED_PATH_PARTS


@dataclass
class AuditReport:
    root: str
    total_files: int = 0
    total_bytes: int = 0
    indexable_files: int = 0
    excluded_files: int = 0
    by_top_level: Dict[str, Dict[str, float]] = field(default_factory=dict)
    excluded_reasons: Dict[str, int] = field(default_factory=dict)
    suspicious_text: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# D&D RAG Data Audit",
            "",
            f"- Root: `{self.root}`",
            f"- Total files: {self.total_files}",
            f"- Total size: {self.total_bytes / 1024 / 1024:.2f} MB",
            f"- Indexable files: {self.indexable_files}",
            f"- Excluded files: {self.excluded_files}",
            "",
            "## Top-Level Buckets",
            "",
            "| Bucket | Files | MB |",
            "|---|---:|---:|",
        ]
        for bucket, stats in sorted(self.by_top_level.items(), key=lambda item: item[1]["bytes"], reverse=True):
            lines.append(f"| {bucket} | {int(stats['files'])} | {stats['bytes'] / 1024 / 1024:.2f} |")
        lines.extend(["", "## Exclusion Reasons", ""])
        if self.excluded_reasons:
            for reason, count in sorted(self.excluded_reasons.items()):
                lines.append(f"- {reason}: {count}")
        else:
            lines.append("- None")
        lines.extend(["", "## Suspicious Text Samples", ""])
        if self.suspicious_text:
            for item in self.suspicious_text[:20]:
                lines.append(f"- `{item}`")
        else:
            lines.append("- None")
        return "\n".join(lines) + "\n"


def audit_source_tree(data_dir: Path) -> AuditReport:
    report = AuditReport(root=str(data_dir))
    for path in sorted(data_dir.rglob("*.json")):
        report.total_files += 1
        size = path.stat().st_size
        report.total_bytes += size
        rel = path.relative_to(data_dir)
        bucket = rel.parts[0] if len(rel.parts) > 1 else path.name
        stats = report.by_top_level.setdefault(bucket, {"files": 0, "bytes": 0})
        stats["files"] += 1
        stats["bytes"] += size
        reason = _exclusion_reason(path, data_dir)
        if reason:
            report.excluded_files += 1
            report.excluded_reasons[reason] = report.excluded_reasons.get(reason, 0) + 1
        else:
            report.indexable_files += 1
            _scan_suspicious_text(path, report)
    return report


def _exclusion_reason(path: Path, data_dir: Path) -> str:
    rel_parts = set(path.relative_to(data_dir).parts)
    if "roll20-module" in rel_parts:
        return "roll20-module"
    if "adventure" in rel_parts:
        return "adventure"
    if path.name in EXCLUDED_FILES:
        return "utility"
    if path.name.startswith("fluff-"):
        return "fluff"
    if rel_parts & EXCLUDED_PATH_PARTS:
        return "excluded-domain"
    return ""


def _scan_suspicious_text(path: Path, report: AuditReport) -> None:
    if len(report.suspicious_text) >= 20 or path.stat().st_size > 2_000_000:
        return
    text = path.read_text(encoding="utf-8", errors="ignore")
    for marker in ["᧿", "\ufffd", "TODO", "FIXME"]:
        if marker in text:
            report.suspicious_text.append(f"{path.name}: contains {marker}")

