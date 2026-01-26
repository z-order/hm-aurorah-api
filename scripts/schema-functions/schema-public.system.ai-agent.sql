/*
   -- Run this SQL to create required core functions 

   Option 1: Using environment from .env.local
   $ psql $POSTGRES_URL < schema.sql
  
   Option 2: Using psql command line
   $ psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -f schema.sql
  
   Option 3: Manually connect and execute:
   $ psql postgresql://your_user:your_password@your_host/your_database < schema.sql
  
   Verify functions were created:
   $ psql $POSTGRES_URL -c "\df"
*/

CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;


/*  au_system_upsert_ai_agent() function
    
    Upsert function using INSERT ... ON CONFLICT ... DO UPDATE:
    - Inserts a new AI agent if not exists
    - Updates if exists and title/keyword/ui_sort_order/description differs
    - Resurrects soft-deleted records by clearing deleted_at

    Example usages:
    au_system_upsert_ai_agent('task_translation_a1', 'Aurorah-A1', 'AI Translation', 'A0', 'First translation agent');  */
CREATE OR REPLACE FUNCTION au_system_upsert_ai_agent(
  p_ai_agent_id VARCHAR(64),
  p_ai_agent_title VARCHAR(64),
  p_ai_agent_keyword VARCHAR(64),
  p_ui_sort_order VARCHAR(64),
  p_description VARCHAR(512)
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_is_insert BOOLEAN;
BEGIN

  -- Upsert using INSERT ... ON CONFLICT ... DO UPDATE
  -- xmax = 0 indicates a fresh insert, xmax > 0 indicates an update
  INSERT INTO au_system_ai_agents (
    ai_agent_id,
    ai_agent_title,
    ai_agent_keyword,
    ui_sort_order,
    description
  ) VALUES (
    p_ai_agent_id,
    p_ai_agent_title,
    p_ai_agent_keyword,
    p_ui_sort_order,
    p_description
  )
  ON CONFLICT (ai_agent_id) DO UPDATE SET
    ai_agent_title = EXCLUDED.ai_agent_title,
    ai_agent_keyword = EXCLUDED.ai_agent_keyword,
    ui_sort_order = EXCLUDED.ui_sort_order,
    description = EXCLUDED.description,
    updated_at = now(),
    deleted_at = NULL  -- Resurrect if soft-deleted
  WHERE au_system_ai_agents.ai_agent_title IS DISTINCT FROM EXCLUDED.ai_agent_title
     OR au_system_ai_agents.ai_agent_keyword IS DISTINCT FROM EXCLUDED.ai_agent_keyword
     OR au_system_ai_agents.ui_sort_order IS DISTINCT FROM EXCLUDED.ui_sort_order
     OR au_system_ai_agents.description IS DISTINCT FROM EXCLUDED.description
     OR au_system_ai_agents.deleted_at IS NOT NULL -- Resurrect if soft-deleted
  RETURNING (xmax = 0) INTO v_is_insert;
  -- v_is_insert is used to determine if the operation was an INSERT or UPDATE
  --   TRUE → xmax = 0 was true → it was an INSERT
  --   FALSE → xmax = 0 was false → it was an UPDATE
  --   NULL → no row returned (no match)

  -- Return result based on operation type
  IF v_is_insert IS NULL THEN
    -- No row returned means ON CONFLICT matched but WHERE clause prevented update (no changes)
    RETURN QUERY SELECT 200, 'AI agent already exists with same values'::TEXT;
  ELSIF v_is_insert THEN
    RETURN QUERY SELECT 201, 'AI agent created successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 200, 'AI agent updated successfully'::TEXT;
  END IF;
END;
$$;


-- au_system_create_ai_agent() function
CREATE OR REPLACE FUNCTION au_system_create_ai_agent(
  p_ai_agent_id VARCHAR(64),
  p_ai_agent_title VARCHAR(64),
  p_ai_agent_keyword VARCHAR(64),
  p_ui_sort_order VARCHAR(64),
  p_description VARCHAR(512)
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_agent_count INT;
BEGIN

  -- Check if the agent already exists
  SELECT COUNT(*) INTO v_agent_count
  FROM au_system_ai_agents
  WHERE au_system_ai_agents.ai_agent_id = p_ai_agent_id
    AND deleted_at IS NULL;

  IF v_agent_count > 0 THEN
    RETURN QUERY SELECT 409, 'AI agent already exists'::TEXT;
    RETURN;
  END IF;

  -- Create the agent
  INSERT INTO au_system_ai_agents (
    ai_agent_id,
    ai_agent_title,
    ai_agent_keyword,
    ui_sort_order,
    description
  ) VALUES (
    p_ai_agent_id,
    p_ai_agent_title,
    p_ai_agent_keyword,
    p_ui_sort_order,
    p_description
  );

  -- Return result
  RETURN QUERY SELECT 200, 'AI agent created successfully'::TEXT;
END;
$$;


-- au_system_update_ai_agent() function
CREATE OR REPLACE FUNCTION au_system_update_ai_agent(
  p_ai_agent_id VARCHAR(64),
  p_ai_agent_title VARCHAR(64) DEFAULT NULL,
  p_ai_agent_keyword VARCHAR(64) DEFAULT NULL,
  p_ui_sort_order VARCHAR(64) DEFAULT NULL,
  p_description VARCHAR(512) DEFAULT NULL
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_updated BOOLEAN;
BEGIN

  -- Update the agent
  UPDATE au_system_ai_agents
  SET
    ai_agent_title = COALESCE(p_ai_agent_title, ai_agent_title),
    ai_agent_keyword = COALESCE(p_ai_agent_keyword, ai_agent_keyword),
    ui_sort_order = COALESCE(p_ui_sort_order, ui_sort_order),
    description = COALESCE(p_description, description),
    updated_at = now()
  WHERE au_system_ai_agents.ai_agent_id = p_ai_agent_id
    AND deleted_at IS NULL;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'AI agent updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'AI agent not found'::TEXT;
  END IF;
END;
$$;


-- au_system_delete_ai_agent() function (soft delete)
CREATE OR REPLACE FUNCTION au_system_delete_ai_agent(
  p_ai_agent_id VARCHAR(64)
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_deleted BOOLEAN;
BEGIN

  -- Delete the agent (soft delete)
  UPDATE au_system_ai_agents
  SET deleted_at = now()
  WHERE au_system_ai_agents.ai_agent_id = p_ai_agent_id
    AND deleted_at IS NULL;

  -- Set v_deleted to TRUE if row was deleted, FALSE otherwise
  v_deleted := FOUND;

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'AI agent deleted successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'AI agent not found'::TEXT;
  END IF;
END;
$$;


/*  au_system_get_ai_agent() function

    Example usages:
    au_system_get_ai_agent();                         -- Get all AI agents
    au_system_get_ai_agent('agent-id');               -- Get specific AI agent  */
CREATE OR REPLACE FUNCTION au_system_get_ai_agent(
  p_ai_agent_id VARCHAR(64) DEFAULT NULL
)
RETURNS TABLE (
  ai_agent_id VARCHAR(64),
  ai_agent_title VARCHAR(64),
  ai_agent_keyword VARCHAR(64),
  ui_sort_order VARCHAR(64),
  description VARCHAR(512),
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_ai_agent_id IS NULL THEN
    -- Get all AI agents
    RETURN QUERY
    SELECT a.ai_agent_id, a.ai_agent_title, a.ai_agent_keyword,
           a.ui_sort_order, a.description, a.created_at, a.updated_at
    FROM au_system_ai_agents a
    WHERE a.deleted_at IS NULL
    ORDER BY a.ui_sort_order ASC, a.ai_agent_title ASC;
  ELSE
    -- Get specific AI agent
    RETURN QUERY
    SELECT a.ai_agent_id, a.ai_agent_title, a.ai_agent_keyword,
           a.ui_sort_order, a.description, a.created_at, a.updated_at
    FROM au_system_ai_agents a
    WHERE a.ai_agent_id = p_ai_agent_id
      AND a.deleted_at IS NULL;
  END IF;
END;
$$;
