from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dnd_rag.adapters import FiveEToolsCnAdapter
from dnd_rag.audit import audit_source_tree
from dnd_rag.service import RagService
from dnd_rag.settings import load_env_file


class AskRequest(BaseModel):
    question: str
    scope: str = "core"


def build_service() -> RagService:
    load_env_file()
    data_dir = os.getenv("FIVEETOOLS_DATA_DIR")
    if data_dir:
        return RagService.from_adapter(FiveEToolsCnAdapter(Path(data_dir)))
    return RagService.from_sample_data()


app = FastAPI(title="D&D Rules Encyclopedia RAG", version="0.1.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
SERVICE = build_service()


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


@app.post("/api/ask")
def ask(request: AskRequest) -> Dict[str, Any]:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    response = SERVICE.ask(request.question.strip(), request.scope)
    return {
        "answer": response.answer,
        "direct_answer": response.direct_answer,
        "supporting_points": response.supporting_points,
        "caveats": response.caveats,
        "mode": response.mode,
        "citations": response.citations,
        "related_entries": [_doc_to_json(doc) for doc in response.related_entries],
        "evidence": [_evidence_to_json(item) for item in response.evidence],
    }


@app.get("/api/entries/{document_id}")
def entry(document_id: str) -> Dict[str, Any]:
    doc = SERVICE.entry(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="entry not found")
    return _doc_to_json(doc, include_body=True)


@app.get("/api/audit")
def audit() -> Dict[str, Any]:
    data_dir = Path(os.getenv("FIVEETOOLS_DATA_DIR", "sample_data/5etools"))
    report = audit_source_tree(data_dir)
    return {
        "root": report.root,
        "total_files": report.total_files,
        "total_mb": round(report.total_bytes / 1024 / 1024, 2),
        "indexable_files": report.indexable_files,
        "excluded_files": report.excluded_files,
        "by_top_level": report.by_top_level,
        "excluded_reasons": report.excluded_reasons,
        "suspicious_text": report.suspicious_text,
    }


@app.post("/api/index/rebuild")
def rebuild_index() -> Dict[str, Any]:
    global SERVICE
    SERVICE = build_service()
    return {"documents": len(SERVICE.documents), "chunks": len(SERVICE.chunks)}


def _doc_to_json(doc, include_body: bool = False) -> Dict[str, Any]:
    data = {
        "id": doc.id,
        "title_zh": doc.title_zh,
        "title_en": doc.title_en,
        "category": doc.category,
        "source_id": doc.source_id,
        "search_scope": doc.search_scope,
        "knowledge_domain": doc.knowledge_domain,
        "summary_text": doc.summary_text,
        "citation": doc.citation.label(),
        "aliases": doc.aliases,
        "semantic_tags": doc.semantic_tags,
    }
    if include_body:
        data["body_text"] = doc.body_text
        data["structured_fields"] = doc.structured_fields
        data["relations"] = [{"type": ref.ref_type, "label": ref.label} for ref in doc.relations]
    return data


def _evidence_to_json(item) -> Dict[str, Any]:
    score = item.score
    return {
        "chunk_id": item.chunk.id,
        "document_id": item.chunk.document_id,
        "title": item.chunk.citation.title,
        "source": item.chunk.source_id,
        "chunk_level": item.chunk.chunk_level,
        "chunk_type": item.chunk.chunk_type,
        "title_path": item.chunk.title_path,
        "display_text": item.chunk.display_text,
        "score": {
            "dense": round(score.dense_score, 3),
            "lexical": round(score.lexical_score, 3),
            "alias": round(score.alias_score, 3),
            "title": round(score.title_score, 3),
            "source": round(score.source_score, 3),
            "structure": round(score.structure_score, 3),
            "final": round(score.final_score, 3),
            "reasons": score.reasons,
        },
    }
