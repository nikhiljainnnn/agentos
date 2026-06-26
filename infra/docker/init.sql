-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Index for vector similarity search (created after tables via alembic)
-- This file runs on first boot to set up extensions
