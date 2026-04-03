---
description: "Use when writing SQL migrations or database schema changes. Covers pgvector usage, UUID primary keys, migration conventions, and safety guards."
applyTo: "db/**/*.sql"
---
# SQL Migration Guidelines

## Conventions
- Migrations are sequentially numbered: `001_initial_schema.sql`, `002_add_index.sql`, etc.
- Always include `IF NOT EXISTS` / `IF EXISTS` guards for idempotent re-runs
- Use `UUID` primary keys with `DEFAULT gen_random_uuid()`
- Use `TIMESTAMPTZ` for all timestamps with `DEFAULT now()`
- Table and column names: `snake_case`

## pgvector
- Enable extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- Embedding columns: `vector(768)` (nomic-embed-text dimension)
- Create HNSW indexes for similarity search: `CREATE INDEX ... USING hnsw (embedding vector_cosine_ops)`
- Use cosine distance operator `<=>` for similarity queries

## Relationships
- Use junction tables for many-to-many: `email_topics`, `summary_topics`, `task_topics`
- Foreign keys with `ON DELETE CASCADE` where appropriate
- Index foreign key columns

## Safety
- Never drop columns or tables in the same migration as code that stops using them
- Add new columns as `NULL` first, then backfill, then add `NOT NULL` constraint
- Test migrations against a copy of production data when possible
