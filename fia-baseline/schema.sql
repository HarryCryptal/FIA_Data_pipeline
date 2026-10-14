-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- NODES TABLE
-- Represents entity concepts (characters, traits, abuse techniques, etc.)
-- ============================================================================
CREATE TABLE nodes (
  id          SERIAL PRIMARY KEY,
  
  -- Entity classification (TWEAK: Expand this list as project requirements grow)
  type        TEXT NOT NULL CHECK (type IN (
                'player_type','red_flag','abuse_technique','vulnerability_trait',
                'trauma_pathway','mental_process','media_character','flavor_of_abuse'
              )),
              
  name        TEXT NOT NULL,
  description TEXT NOT NULL CHECK (length(description) > 0),
  
  -- Vector embedding for semantic search (384-dim: e.g., sentence-transformers)
  -- TWEAK: Change 384 to 1536 if using OpenAI text-embedding-3-small
  embedding   vector(384),
  
  -- Flexible JSON container for extra attributes (e.g., {"severity": "high", "source": "book"})
  metadata    JSONB DEFAULT '{}'::jsonb NOT NULL,
  
  created_at  TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

  UNIQUE (type, name)
);

-- ============================================================================
-- EDGES TABLE
-- Directed graph relationships between nodes
-- ============================================================================
CREATE TABLE edges (
  src_id     INT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  dst_id     INT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  
  -- Relationship type (TWEAK: Tweak/add edge types here as graph design evolves)
  rel_type   TEXT NOT NULL CHECK (rel_type IN (
               'HAS_RED_FLAG','USES','TARGETS','EXPLOITS','PRODUCES',
               'ACCOMPANIES','OPERATES_IN','EXEMPLIFIES'
             )),
             
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,

  PRIMARY KEY (src_id, dst_id, rel_type)
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Fast lookup for bidirectional graph traversal
CREATE INDEX edges_src_idx ON edges (src_id, rel_type);
CREATE INDEX edges_dst_idx ON edges (dst_id, rel_type);

-- Filter nodes by type quickly
CREATE INDEX nodes_type_idx ON nodes (type);

-- JSONB GIN index for querying node metadata tags
CREATE INDEX nodes_metadata_idx ON nodes USING gin (metadata);

-- HNSW Vector Index for fast semantic similarity search (Cosine distance)
-- Note: Populate table with some data before running heavy ANN queries
CREATE INDEX nodes_embedding_idx ON nodes USING hnsw (embedding vector_cosine_ops);