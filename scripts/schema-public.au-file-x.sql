/*
   -- Run this SQL to create required au_file_* tables 

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


-- au_file_nodes
CREATE TABLE IF NOT EXISTS au_file_nodes (
    file_id UUID NOT NULL DEFAULT uuidv7(),
    owner_id TEXT NOT NULL,
    parent_file_id UUID NULL,
    file_type VARCHAR(32) DEFAULT 'folder',
    file_name VARCHAR(512) NOT NULL,
    file_url VARCHAR(1024) NULL,
    file_ext VARCHAR(32) NOT NULL,
    file_size BIGINT NOT NULL,
    mime_type VARCHAR(32) NULL,
    description VARCHAR(512) NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
); 

ALTER TABLE au_file_nodes ADD CONSTRAINT pk_au_file_nodes PRIMARY KEY (file_id);
ALTER TABLE au_file_nodes ADD CONSTRAINT fk_au_file_nodes_parent_file_id FOREIGN KEY (parent_file_id) REFERENCES au_file_nodes(file_id);
CREATE INDEX IF NOT EXISTS idx_au_file_nodes_parent_file_id ON au_file_nodes(parent_file_id ASC NULLS FIRST);
CREATE INDEX IF NOT EXISTS idx_au_file_nodes_I1
    ON au_file_nodes
    (owner_id ASC, 
     parent_file_id DESC NULLS FIRST, 
     updated_at DESC, 
     deleted_at DESC NULLS LAST)
    WITH (fillfactor=100);
CREATE INDEX IF NOT EXISTS idx_au_file_nodes_I2
    ON au_file_nodes
    (owner_id ASC, 
     updated_at DESC, 
     deleted_at DESC NULLS LAST)
    WITH (fillfactor=100);


-- au_file_acl
CREATE TABLE IF NOT EXISTS au_file_acl (
    file_id UUID NOT NULL,
    principal_id UUID NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE au_file_acl ADD CONSTRAINT pk_au_file_acl PRIMARY KEY (file_id, principal_id);
ALTER TABLE au_file_acl ADD CONSTRAINT fk_au_file_acl_file_id FOREIGN KEY (file_id) REFERENCES au_file_nodes(file_id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_au_file_acl_file_id ON au_file_acl(file_id);
CREATE INDEX IF NOT EXISTS idx_au_file_acl_principal_id ON au_file_acl(principal_id);


-- au_file_tasks
CREATE TABLE IF NOT EXISTS au_file_tasks (
    file_id UUID NOT NULL,
    file_preset_id UUID NOT NULL,
    original_id UUID NOT NULL,
    translation_id_1st UUID NOT NULL,
    translation_id_2nd UUID NOT NULL,
    proofreading_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE au_file_tasks ADD CONSTRAINT pk_au_file_tasks PRIMARY KEY (file_id);
ALTER TABLE au_file_tasks ADD CONSTRAINT fk_au_file_tasks_file_id FOREIGN KEY (file_id) REFERENCES au_file_nodes(file_id) ON DELETE CASCADE;


-- au_file_presets
CREATE TABLE IF NOT EXISTS au_file_presets (
    file_preset_id UUID NOT NULL DEFAULT uuidv7(),
    principal_id UUID NOT NULL,
    description VARCHAR(128) NOT NULL,
    translation_memory VARCHAR(256) NULL,
    translation_role TEXT NULL,
    translation_rule TEXT NULL,
    target_language VARCHAR(128) NOT NULL,
    target_country VARCHAR(128) NOT NULL,
    target_city VARCHAR(128) NULL,
    task_type VARCHAR(32) NOT NULL DEFAULT 'localization',
    audience text NOT NULL DEFAULT 'general',
    purpose text NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);

ALTER TABLE au_file_presets ADD CONSTRAINT pk_au_file_presets PRIMARY KEY (file_preset_id);
CREATE INDEX IF NOT EXISTS idx_au_file_presets_I1
    ON au_file_presets
    (principal_id ASC, 
     updated_at DESC, 
     deleted_at DESC NULLS LAST)
    WITH (fillfactor=100);


-- au_file_original
CREATE TABLE IF NOT EXISTS au_file_original (
    original_id UUID NOT NULL DEFAULT uuidv7(),
    file_id UUID NOT NULL,
    original_text JSONB NOT NULL,
    original_text_modified JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE au_file_original ADD CONSTRAINT pk_au_file_original PRIMARY KEY (original_id);
ALTER TABLE au_file_original ADD CONSTRAINT fk_au_file_original_file_id FOREIGN KEY (file_id) REFERENCES au_file_nodes(file_id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_au_file_original_file_id ON au_file_original(file_id);


-- au_file_translation
CREATE TABLE IF NOT EXISTS au_file_translation (
    translation_id UUID NOT NULL DEFAULT uuidv7(),
    file_id UUID NOT NULL,
    file_preset_id UUID NOT NULL,
    file_preset_json JSON NOT NULL,
    assignee_id UUID NOT NULL,
    llm_model_id UUID NOT NULL,
    llm_model_temperature INT NOT NULL,
    agent_task_name VARCHAR(256) NOT NULL DEFAULT 'task_translation_1st',
    translation_text JSONB NULL,
    translation_text_modified JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);

ALTER TABLE au_file_translation ADD CONSTRAINT pk_au_file_translation PRIMARY KEY (translation_id);
ALTER TABLE au_file_translation ADD CONSTRAINT fk_au_file_translation_file_id FOREIGN KEY (file_id) REFERENCES au_file_nodes(file_id) ON DELETE CASCADE;
ALTER TABLE au_file_translation ADD CONSTRAINT fk_au_file_translation_file_preset_id FOREIGN KEY (file_preset_id) REFERENCES au_file_presets(file_preset_id);
CREATE INDEX IF NOT EXISTS idx_au_file_translation_I1
    ON au_file_translation
    (file_id DESC, 
     created_at DESC, 
     deleted_at DESC NULLS LAST)
    WITH (fillfactor=100);


-- au_file_proofreadming
CREATE TABLE IF NOT EXISTS au_file_proofreading (
    proofreading_id UUID NOT NULL DEFAULT uuidv7(),
    file_id UUID NOT NULL,
    assignee_id UUID NULL,  -- Reserverd for future use
    participant_ids UUID[] NULL,  -- Reserverd for future use
    proofreaded_text JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    deleted_at TIMESTAMPTZ NULL
);

ALTER TABLE au_file_proofreading ADD CONSTRAINT pk_au_file_proofreading PRIMARY KEY (proofreading_id);
ALTER TABLE au_file_proofreading ADD CONSTRAINT fk_au_file_proofreading_file_id FOREIGN KEY (file_id) REFERENCES au_file_nodes(file_id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_au_file_proofreading_I1
    ON au_file_proofreading
    (file_id DESC, 
     created_at DESC, 
     deleted_at DESC NULLS LAST)
    WITH (fillfactor=100);


-- au_file_edit_history
CREATE TABLE IF NOT EXISTS au_file_edit_history (
    history_id UUID NOT NULL DEFAULT uuidv7(),
    file_id UUID NOT NULL,
    target_type VARCHAR(32) NOT NULL,
    target_id UUID NOT NULL,
    marker_number INT NOT NULL,
    editor_id UUID NOT NULL,
    text_before TEXT NULL,
    text_after TEXT NOT NULL,
    comments TEXT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE au_file_edit_history ADD CONSTRAINT pk_au_file_edit_history PRIMARY KEY (history_id);
ALTER TABLE au_file_edit_history ADD CONSTRAINT fk_au_file_edit_history_file_id FOREIGN KEY (file_id) REFERENCES au_file_nodes(file_id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_au_file_edit_history_I1
    ON au_file_edit_history
    (file_id DESC, 
     target_type ASC,
     target_id ASC,
     marker_number ASC,
     created_at DESC)
    WITH (fillfactor=100);


-- au_file_checkpoint
CREATE TABLE IF NOT EXISTS au_file_checkpoint (
    checkpoint_id UUID NOT NULL DEFAULT uuidv7(),
    file_id UUID NOT NULL,
    history_id UUID NOT NULL,
    original_text_modified JSONB NULL,
    translation_text_modified JSONB NULL,
    proofreaded_text JSONB NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE au_file_checkpoint ADD CONSTRAINT pk_au_file_checkpoint PRIMARY KEY (checkpoint_id);
ALTER TABLE au_file_checkpoint ADD CONSTRAINT fk_au_file_checkpoint_file_id FOREIGN KEY (file_id) REFERENCES au_file_nodes(file_id) ON DELETE CASCADE;
ALTER TABLE au_file_checkpoint ADD CONSTRAINT fk_au_file_checkpoint_history_id FOREIGN KEY (history_id) REFERENCES au_file_edit_history(history_id);
CREATE INDEX IF NOT EXISTS idx_au_file_checkpoint_I1
    ON au_file_checkpoint
    (file_id DESC, 
     history_id DESC)
    WITH (fillfactor=100);


-- Foreign keys
ALTER TABLE au_file_tasks ADD CONSTRAINT fk_au_file_tasks_file_original_id FOREIGN KEY (original_id) REFERENCES au_file_original(original_id);
ALTER TABLE au_file_tasks ADD CONSTRAINT fk_au_file_tasks_file_translation_id_1st FOREIGN KEY (translation_id_1st) REFERENCES au_file_translation(translation_id);
ALTER TABLE au_file_tasks ADD CONSTRAINT fk_au_file_tasks_file_translation_id_2nd FOREIGN KEY (translation_id_2nd) REFERENCES au_file_translation(translation_id);
ALTER TABLE au_file_tasks ADD CONSTRAINT fk_au_file_tasks_file_proofreading_id FOREIGN KEY (proofreading_id) REFERENCES au_file_proofreading(proofreading_id);
-- ALTER TABLE au_file_translation ADD CONSTRAINT fk_au_file_translation_llm_model_id FOREIGN KEY (llm_model_id) REFERENCES au_system_models(llm_model_id);
