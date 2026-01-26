/*
   -- Run this SQL to create required au_system_* tables 

   Option 1: Using environment from .env.local
   $ psql $POSTGRES_URL < schema.sql
  
   Option 2: Using psql command line
   $ psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -f schema.sql
  
   Option 3: Manually connect and execute:
   $ psql postgresql://your_user:your_password@your_host/your_database < schema.sql
  
   Verify tables were created:
   $ psql $POSTGRES_URL -c "\dt"
*/

CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;

-- Enable UUID generation (either pgcrypto or uuid-ossp)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- Crypto & random bytes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- UUIDv1–v5


-- fillfactor=100: packs rows tightly for faster sequential scans, ideal for read-heavy tables.
-- autovacuum_vacuum_scale_factor=1.0 and autovacuum_analyze_scale_factor=1.0
-- autovacuum triggers only when dead tuples reach 100% of live rows, suitable for very infrequent writes.

-- au_system_llm_models
CREATE TABLE IF NOT EXISTS au_system_llm_models (
    llm_model_id VARCHAR(64) NOT NULL,
    llm_model_title VARCHAR(64) NOT NULL,
    llm_model_keyword VARCHAR(64) NOT NULL,
    ui_sort_order VARCHAR(64) NOT NULL DEFAULT 'A0',
    description VARCHAR(512) NULL,
    provider VARCHAR(64) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
) WITH (fillfactor=100, autovacuum_vacuum_scale_factor=1.0, autovacuum_analyze_scale_factor=1.0);

ALTER TABLE au_system_llm_models ADD CONSTRAINT pk_au_system_llm_models PRIMARY KEY (llm_model_id);
CREATE INDEX IF NOT EXISTS idx_au_system_llm_models_I1
    ON au_system_llm_models
    (ui_sort_order ASC, 
     llm_model_title ASC, 
     deleted_at DESC NULLS LAST)
    WITH (fillfactor=100);


-- au_system_ai_agents
CREATE TABLE IF NOT EXISTS au_system_ai_agents (
    ai_agent_id VARCHAR(64) NOT NULL,
    ai_agent_title VARCHAR(64) NOT NULL,
    ai_agent_keyword VARCHAR(64) NOT NULL,
    ui_sort_order VARCHAR(64) NOT NULL DEFAULT 'A0',
    description VARCHAR(512) NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
) WITH (fillfactor=100, autovacuum_vacuum_scale_factor=1.0, autovacuum_analyze_scale_factor=1.0);

ALTER TABLE au_system_ai_agents ADD CONSTRAINT pk_au_system_ai_agents PRIMARY KEY (ai_agent_id);
CREATE INDEX IF NOT EXISTS idx_au_system_ai_agents_I1
    ON au_system_ai_agents
    (ui_sort_order ASC, 
     ai_agent_title ASC, 
     deleted_at DESC NULLS LAST)
    WITH (fillfactor=100);
