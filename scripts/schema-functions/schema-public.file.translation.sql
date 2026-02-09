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


-- au_create_file_translation() function
CREATE OR REPLACE FUNCTION au_create_file_translation(
  p_file_id UUID,
  p_file_preset_id UUID,
  p_file_preset_json JSON,
  p_assignee_id UUID,
  p_translated_text JSONB DEFAULT NULL
)
RETURNS TABLE (
  status INT,
  message TEXT,
  translation_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_file_count INT;
  v_file_preset_count INT;
  v_translation_id UUID;
BEGIN

  -- Check if the file exists
  SELECT COUNT(*) INTO v_file_count
  FROM au_file_nodes
  WHERE au_file_nodes.file_id = p_file_id
    AND deleted_at IS NULL;

  IF v_file_count = 0 THEN
    RETURN QUERY SELECT 404, 'File not found'::TEXT, NULL::UUID;
    RETURN;
  END IF;
  
  -- Check if the file preset exists
  SELECT COUNT(*) INTO v_file_preset_count
  FROM au_file_presets
  WHERE au_file_presets.file_preset_id = p_file_preset_id
    AND deleted_at IS NULL;

  IF v_file_preset_count = 0 THEN
    RETURN QUERY SELECT 404, 'File preset not found'::TEXT, NULL::UUID;
    RETURN;
  END IF;

  -- Create the translation
  INSERT INTO au_file_translation (
    file_id,
    file_preset_id,
    file_preset_json,
    assignee_id,
    translated_text
  ) VALUES (
    p_file_id,
    p_file_preset_id,
    p_file_preset_json,
    p_assignee_id,
    p_translated_text
  )
  RETURNING au_file_translation.translation_id INTO v_translation_id;

  -- Return result
  RETURN QUERY SELECT 200, 'File translation created successfully'::TEXT, v_translation_id;
END;
$$;


-- au_update_file_translation() function
CREATE OR REPLACE FUNCTION au_update_file_translation(
  p_translation_id UUID,
  p_translated_text JSONB DEFAULT NULL,
  p_translated_text_modified JSONB DEFAULT NULL,
  p_ai_agent_data JSON DEFAULT NULL,
  p_status VARCHAR(32) DEFAULT NULL,
  p_message TEXT DEFAULT NULL
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

  -- Update the translation
  UPDATE au_file_translation
  SET
    translated_text = COALESCE(p_translated_text, au_file_translation.translated_text),
    translated_text_modified = COALESCE(p_translated_text_modified, au_file_translation.translated_text_modified),
    ai_agent_data = COALESCE(p_ai_agent_data, au_file_translation.ai_agent_data),
    status = COALESCE(p_status, au_file_translation.status),
    message = COALESCE(p_message, au_file_translation.message),
    updated_at = now()
  WHERE au_file_translation.translation_id = p_translation_id
    AND au_file_translation.deleted_at IS NULL;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'File translation updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File translation not found'::TEXT;
  END IF;
END;
$$;


-- au_delete_file_translation() function (soft delete)
CREATE OR REPLACE FUNCTION au_delete_file_translation(
  p_translation_id UUID
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

  -- Delete the translation (soft delete)
  UPDATE au_file_translation
  SET deleted_at = now()
  WHERE au_file_translation.translation_id = p_translation_id
    AND deleted_at IS NULL;

  -- Set v_deleted to TRUE if row was deleted, FALSE otherwise
  v_deleted := FOUND;

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'File translation deleted successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File translation not found'::TEXT;
  END IF;
END;
$$;


/*  au_get_file_translation_for_listing() function

    Example usages:
    au_get_file_translation_for_listing('file-id');                     -- Get all translations for a file
    au_get_file_translation_for_listing('file-id', 'translation-id');   -- Get specific translation  */
CREATE OR REPLACE FUNCTION au_get_file_translation_for_listing(
  p_file_id UUID,
  p_translation_id UUID DEFAULT NULL
)
RETURNS TABLE (
  translation_id UUID,
  file_id UUID,
  file_preset_id UUID,
  file_preset_json JSON,
  assignee_id UUID,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_translation_id IS NULL THEN
    -- Get all translations for the file
    RETURN QUERY
    SELECT t.translation_id, t.file_id, t.file_preset_id, t.file_preset_json,
           t.assignee_id, t.created_at, t.updated_at
    FROM au_file_translation t
    WHERE t.file_id = p_file_id
      AND t.deleted_at IS NULL
    ORDER BY t.created_at DESC;
  ELSE
    -- Get specific translation
    RETURN QUERY
    SELECT t.translation_id, t.file_id, t.file_preset_id, t.file_preset_json,
           t.assignee_id, t.created_at, t.updated_at
    FROM au_file_translation t
    WHERE t.file_id = p_file_id
      AND t.translation_id = p_translation_id
      AND t.deleted_at IS NULL;
  END IF;
END;
$$;


/*  au_get_file_translation_for_jsonb() function

    Example usages:
    au_get_file_translation_for_jsonb('file-id');                       -- Get all translations for a file
    au_get_file_translation_for_jsonb('file-id', 'translation-id');     -- Get specific translation  */
CREATE OR REPLACE FUNCTION au_get_file_translation_for_jsonb(
  p_file_id UUID,
  p_translation_id UUID DEFAULT NULL
)
RETURNS TABLE (
  translation_id UUID,
  file_id UUID,
  file_preset_id UUID,
  file_preset_json JSON,
  assignee_id UUID,
  translated_text JSONB,
  translated_text_modified JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_translation_id IS NULL THEN
    -- Get all translations for the file
    RETURN QUERY
    SELECT t.translation_id, t.file_id, t.file_preset_id, t.file_preset_json,
           t.assignee_id, t.translated_text, t.translated_text_modified,
           t.created_at, t.updated_at
    FROM au_file_translation t
    WHERE t.file_id = p_file_id
      AND t.deleted_at IS NULL
    ORDER BY t.created_at DESC;
  ELSE
    -- Get specific translation
    RETURN QUERY
    SELECT t.translation_id, t.file_id, t.file_preset_id, t.file_preset_json,
           t.assignee_id, t.translated_text, t.translated_text_modified,
           t.created_at, t.updated_at
    FROM au_file_translation t
    WHERE t.file_id = p_file_id
      AND t.translation_id = p_translation_id
      AND t.deleted_at IS NULL;
  END IF;
END;
$$;
