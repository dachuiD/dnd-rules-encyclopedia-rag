from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from dnd_rag.adapters import FiveEToolsCnAdapter
from dnd_rag.audit import audit_source_tree
from dnd_rag.chunking import build_chunks
from dnd_rag.embedding_index import filter_fresh_rows, load_embedding_index, text_hash
from dnd_rag.providers import DashScopeEmbeddingProvider, DeepSeekLLMProvider, HashEmbeddingProvider
from dnd_rag.service import RagService
from dnd_rag.settings import load_env_file


class AskRequest(BaseModel):
    question: str
    scope: str = "core"


def build_service() -> RagService:
    load_env_file()
    data_dir = os.getenv("FIVEETOOLS_DATA_DIR")
    adapter = FiveEToolsCnAdapter(Path(data_dir)) if data_dir else FiveEToolsCnAdapter.sample()
    documents = adapter.load_documents()
    chunks = [chunk for doc in documents for chunk in build_chunks(doc)]
    embedding_provider = _query_embedding_provider(bool(os.getenv("EMBEDDING_INDEX_PATH")))
    chunk_embeddings = _load_chunk_embeddings(chunks)
    llm_provider = _answer_provider()
    return RagService(
        documents,
        chunks,
        chunk_embeddings=chunk_embeddings,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
    )


def create_app(service: RagService | None = None, gateway_token: str | None = None) -> FastAPI:
    app = FastAPI(title="D&D Rules Encyclopedia RAG", version="0.1.0")
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.state.service = service or build_service()
    app.state.gateway_token = gateway_token if gateway_token is not None else os.getenv("RAG_GATEWAY_TOKEN", "")
    if _env_flag("REQUIRE_GATEWAY_TOKEN") and not app.state.gateway_token:
        raise RuntimeError("RAG_GATEWAY_TOKEN is required when REQUIRE_GATEWAY_TOKEN is enabled")

    @app.middleware("http")
    async def require_gateway_token(request: Request, call_next):
        token = app.state.gateway_token
        if token and request.url.path.startswith("/api/"):
            supplied = request.headers.get("X-RAG-GATEWAY-TOKEN", "")
            if supplied != token:
                return JSONResponse({"detail": "gateway token required"}, status_code=401)
        return await call_next(request)

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse("static/index.html")

    @app.get("/healthz")
    def healthz() -> Dict[str, Any]:
        current = app.state.service
        return {
            "status": "ok",
            "documents": len(current.documents),
            "chunks": len(current.chunks),
            "embeddings": len(current.chunk_embeddings),
            "query_embedding_provider": type(current.embedding_provider).__name__ if current.embedding_provider else None,
            "answer_provider": type(current.llm_provider).__name__ if current.llm_provider else "template",
        }

    @app.post("/api/ask")
    def ask(request: AskRequest) -> Dict[str, Any]:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="question is required")
        response = app.state.service.ask(request.question.strip(), request.scope)
        return {
            "answer": response.answer,
            "direct_answer": response.direct_answer,
            "supporting_points": response.supporting_points,
            "caveats": response.caveats,
            "mode": response.mode,
            "is_multi_hop": response.is_multi_hop,
            "coverage_score": response.coverage_score,
            "missing_requirements": response.missing_requirements,
            "evidence_requirements": response.evidence_requirements,
            "citations": response.citations,
            "related_entries": [_doc_to_json(doc) for doc in response.related_entries],
            "evidence": [_evidence_to_json(item) for item in response.evidence],
        }

    @app.get("/api/entries/{document_id}")
    def entry(document_id: str) -> Dict[str, Any]:
        doc = app.state.service.entry(document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="entry not found")
        return _doc_to_json(doc, include_body=True)

    @app.get("/api/audit")
    def audit() -> Dict[str, Any]:
        data_root = Path(os.getenv("FIVEETOOLS_DATA_DIR", "sample_data/5etools"))
        report = audit_source_tree(data_root)
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
        app.state.service = build_service()
        return {"documents": len(app.state.service.documents), "chunks": len(app.state.service.chunks)}

    return app


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _query_embedding_provider(index_enabled: bool):
    provider = os.getenv("QUERY_EMBEDDING_PROVIDER", "dashscope" if index_enabled else "none").lower()
    if provider == "none":
        return None
    if provider == "hash":
        dimensions = int(os.getenv("DASHSCOPE_EMBEDDING_DIMENSIONS", "64"))
        return HashEmbeddingProvider(dimensions=dimensions)
    if provider == "dashscope":
        return DashScopeEmbeddingProvider()
    raise RuntimeError(f"Unsupported QUERY_EMBEDDING_PROVIDER: {provider}")


def _answer_provider():
    provider = os.getenv("ANSWER_PROVIDER", "template").lower()
    if provider in {"", "template", "none"}:
        return None
    if provider == "deepseek":
        return DeepSeekLLMProvider()
    raise RuntimeError(f"Unsupported ANSWER_PROVIDER: {provider}")


def _load_chunk_embeddings(chunks) -> Dict[str, list[float]]:
    index_path = os.getenv("EMBEDDING_INDEX_PATH")
    if not index_path:
        return {}
    model = os.getenv("DASHSCOPE_EMBEDDING_MODEL", "text-embedding-v4")
    dimensions = int(os.getenv("DASHSCOPE_EMBEDDING_DIMENSIONS", "1024"))
    rows = load_embedding_index(Path(index_path))
    expected_hashes = {chunk.id: text_hash(chunk.embedding_text) for chunk in chunks}
    fresh = filter_fresh_rows(rows, expected_hashes, model=model, dimensions=dimensions)
    return {chunk_id: row.embedding for chunk_id, row in fresh.items()}


app = create_app()


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
