CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS rule_documents (
  id TEXT PRIMARY KEY,
  title_zh TEXT NOT NULL,
  title_en TEXT,
  category TEXT NOT NULL,
  source_id TEXT NOT NULL,
  source_group TEXT NOT NULL CHECK (source_group IN ('core', 'expansion')),
  search_scope TEXT NOT NULL CHECK (search_scope IN ('core', 'full')),
  knowledge_domain TEXT NOT NULL CHECK (knowledge_domain IN ('rules', 'entity', 'lore', 'adventure', 'utility')),
  aliases JSONB NOT NULL DEFAULT '[]',
  summary_text TEXT NOT NULL DEFAULT '',
  body_text TEXT NOT NULL DEFAULT '',
  structured_fields JSONB NOT NULL DEFAULT '{}',
  citation JSONB NOT NULL DEFAULT '{}',
  raw_ref TEXT NOT NULL,
  raw_json JSONB NOT NULL DEFAULT '{}',
  semantic_tags JSONB NOT NULL DEFAULT '[]',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rule_chunks (
  id TEXT PRIMARY KEY,
  document_id TEXT NOT NULL REFERENCES rule_documents(id) ON DELETE CASCADE,
  parent_chunk_id TEXT REFERENCES rule_chunks(id) ON DELETE SET NULL,
  chunk_level TEXT NOT NULL CHECK (chunk_level IN ('parent', 'child')),
  chunk_type TEXT NOT NULL,
  title_path JSONB NOT NULL DEFAULT '[]',
  text TEXT NOT NULL,
  embedding_text TEXT NOT NULL,
  display_text TEXT NOT NULL,
  semantic_tags JSONB NOT NULL DEFAULT '[]',
  citation JSONB NOT NULL DEFAULT '{}',
  source_id TEXT NOT NULL,
  search_scope TEXT NOT NULL CHECK (search_scope IN ('core', 'full')),
  knowledge_domain TEXT NOT NULL,
  category TEXT NOT NULL,
  aliases JSONB NOT NULL DEFAULT '[]',
  embedding vector(1024),
  search_vector tsvector GENERATED ALWAYS AS (
    to_tsvector('simple', coalesce(embedding_text, '') || ' ' || coalesce(display_text, ''))
  ) STORED
);

CREATE TABLE IF NOT EXISTS rule_relations (
  id BIGSERIAL PRIMARY KEY,
  from_document_id TEXT NOT NULL REFERENCES rule_documents(id) ON DELETE CASCADE,
  to_label TEXT NOT NULL,
  relation_type TEXT NOT NULL,
  confidence REAL NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS eval_questions (
  id TEXT PRIMARY KEY,
  question_zh TEXT NOT NULL,
  question_original TEXT,
  source_language TEXT NOT NULL,
  provenance TEXT NOT NULL,
  scope TEXT NOT NULL CHECK (scope IN ('core', 'full')),
  expected_documents JSONB NOT NULL DEFAULT '[]',
  expected_chunks JSONB NOT NULL DEFAULT '[]',
  expected_terms JSONB NOT NULL DEFAULT '[]',
  must_include JSONB NOT NULL DEFAULT '[]',
  must_not_include JSONB NOT NULL DEFAULT '[]',
  difficulty TEXT NOT NULL,
  question_type TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rule_chunks_scope_domain ON rule_chunks(search_scope, knowledge_domain);
CREATE INDEX IF NOT EXISTS idx_rule_chunks_source ON rule_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_rule_chunks_search_vector ON rule_chunks USING gin(search_vector);
CREATE INDEX IF NOT EXISTS idx_rule_chunks_embedding ON rule_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
