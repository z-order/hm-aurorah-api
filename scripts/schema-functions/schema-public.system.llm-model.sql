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


/*  au_system_upsert_llm_model() function
    
    Upsert function: inserts a new LLM model if not exists,
    updates if exists and title/keyword/ui_sort_order/description/provider differs.

    Example usages:
    au_system_upsert_llm_model('gpt-4o', 'OpenAI GPT-4o', 'Flagship model', 'A0', 'Multi-modal AI', 'openai');  */
CREATE OR REPLACE FUNCTION au_system_upsert_llm_model(
  p_llm_model_id VARCHAR(64),
  p_llm_model_title VARCHAR(64),
  p_llm_model_keyword VARCHAR(64),
  p_ui_sort_order VARCHAR(64),
  p_description VARCHAR(512),
  p_provider VARCHAR(64)
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
  INSERT INTO au_system_llm_models (
    llm_model_id,
    llm_model_title,
    llm_model_keyword,
    ui_sort_order,
    description,
    provider
  ) VALUES (
    p_llm_model_id,
    p_llm_model_title,
    p_llm_model_keyword,
    p_ui_sort_order,
    p_description,
    p_provider
  )
  ON CONFLICT (llm_model_id) DO UPDATE SET
    llm_model_title = EXCLUDED.llm_model_title,
    llm_model_keyword = EXCLUDED.llm_model_keyword,
    ui_sort_order = EXCLUDED.ui_sort_order,
    description = EXCLUDED.description,
    provider = EXCLUDED.provider,
    updated_at = now(),
    deleted_at = NULL  -- Resurrect if soft-deleted
  WHERE au_system_llm_models.llm_model_title IS DISTINCT FROM EXCLUDED.llm_model_title
     OR au_system_llm_models.llm_model_keyword IS DISTINCT FROM EXCLUDED.llm_model_keyword
     OR au_system_llm_models.ui_sort_order IS DISTINCT FROM EXCLUDED.ui_sort_order
     OR au_system_llm_models.description IS DISTINCT FROM EXCLUDED.description
     OR au_system_llm_models.provider IS DISTINCT FROM EXCLUDED.provider
     OR au_system_llm_models.deleted_at IS NOT NULL  -- Resurrect if soft-deleted
  RETURNING (xmax = 0) INTO v_is_insert;
  -- v_is_insert is used to determine if the operation was an INSERT or UPDATE
  --   TRUE → xmax = 0 was true → it was an INSERT
  --   FALSE → xmax = 0 was false → it was an UPDATE
  --   NULL → no row returned (no match)

  -- Return result based on operation type
  IF v_is_insert IS NULL THEN
    -- No row returned means ON CONFLICT matched but WHERE clause prevented update (no changes)
    RETURN QUERY SELECT 200, 'LLM model already exists with same values'::TEXT;
  ELSIF v_is_insert THEN
    RETURN QUERY SELECT 201, 'LLM model created successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 200, 'LLM model updated successfully'::TEXT;
  END IF;
END;
$$;


-- au_system_create_llm_model() function
CREATE OR REPLACE FUNCTION au_system_create_llm_model(
  p_llm_model_id VARCHAR(64),
  p_llm_model_title VARCHAR(64),
  p_llm_model_keyword VARCHAR(64),
  p_ui_sort_order VARCHAR(64),
  p_description VARCHAR(512),
  p_provider VARCHAR(64)
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_model_count INT;
BEGIN

  -- Check if the model already exists
  SELECT COUNT(*) INTO v_model_count
  FROM au_system_llm_models
  WHERE au_system_llm_models.llm_model_id = p_llm_model_id
    AND deleted_at IS NULL;

  IF v_model_count > 0 THEN
    RETURN QUERY SELECT 409, 'LLM model already exists'::TEXT;
    RETURN;
  END IF;

  -- Create the model
  INSERT INTO au_system_llm_models (
    llm_model_id,
    llm_model_title,
    llm_model_keyword,
    ui_sort_order,
    description,
    provider
  ) VALUES (
    p_llm_model_id,
    p_llm_model_title,
    p_llm_model_keyword,
    p_ui_sort_order,
    p_description,
    p_provider
  );

  -- Return result
  RETURN QUERY SELECT 200, 'LLM model created successfully'::TEXT;
END;
$$;


-- au_system_update_llm_model() function
CREATE OR REPLACE FUNCTION au_system_update_llm_model(
  p_llm_model_id VARCHAR(64),
  p_llm_model_title VARCHAR(64) DEFAULT NULL,
  p_llm_model_keyword VARCHAR(64) DEFAULT NULL,
  p_ui_sort_order VARCHAR(64) DEFAULT NULL,
  p_description VARCHAR(512) DEFAULT NULL,
  p_provider VARCHAR(64) DEFAULT NULL
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

  -- Update the model
  UPDATE au_system_llm_models
  SET
    llm_model_title = COALESCE(p_llm_model_title, llm_model_title),
    llm_model_keyword = COALESCE(p_llm_model_keyword, llm_model_keyword),
    ui_sort_order = COALESCE(p_ui_sort_order, ui_sort_order),
    description = COALESCE(p_description, description),
    provider = COALESCE(p_provider, provider),
    updated_at = now()
  WHERE au_system_llm_models.llm_model_id = p_llm_model_id
    AND deleted_at IS NULL;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'LLM model updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'LLM model not found'::TEXT;
  END IF;
END;
$$;


-- au_system_delete_llm_model() function (soft delete)
CREATE OR REPLACE FUNCTION au_system_delete_llm_model(
  p_llm_model_id VARCHAR(64)
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

  -- Delete the model (soft delete)
  UPDATE au_system_llm_models
  SET deleted_at = now()
  WHERE au_system_llm_models.llm_model_id = p_llm_model_id
    AND deleted_at IS NULL;

  -- Set v_deleted to TRUE if row was deleted, FALSE otherwise
  v_deleted := FOUND;

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'LLM model deleted successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'LLM model not found'::TEXT;
  END IF;
END;
$$;


/*  au_system_get_llm_model() function

    Example usages:
    au_system_get_llm_model();                        -- Get all LLM models
    au_system_get_llm_model('model-id');              -- Get specific LLM model  */
CREATE OR REPLACE FUNCTION au_system_get_llm_model(
  p_llm_model_id VARCHAR(64) DEFAULT NULL
)
RETURNS TABLE (
  llm_model_id VARCHAR(64),
  llm_model_title VARCHAR(64),
  llm_model_keyword VARCHAR(64),
  ui_sort_order VARCHAR(64),
  description VARCHAR(512),
  provider VARCHAR(64),
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_llm_model_id IS NULL THEN
    -- Get all LLM models
    RETURN QUERY
    SELECT m.llm_model_id, m.llm_model_title, m.llm_model_keyword,
           m.ui_sort_order, m.description, m.provider, m.created_at, m.updated_at
    FROM au_system_llm_models m
    WHERE m.deleted_at IS NULL
    ORDER BY m.ui_sort_order ASC, m.llm_model_title ASC;
  ELSE
    -- Get specific LLM model
    RETURN QUERY
    SELECT m.llm_model_id, m.llm_model_title, m.llm_model_keyword,
           m.ui_sort_order, m.description, m.provider, m.created_at, m.updated_at
    FROM au_system_llm_models m
    WHERE m.llm_model_id = p_llm_model_id
      AND m.deleted_at IS NULL;
  END IF;
END;
$$;
