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


-- au_create_file_preset() function
CREATE OR REPLACE FUNCTION au_create_file_preset(
  p_principal_id UUID,
  p_description VARCHAR(128),
  p_llm_model_id VARCHAR(64),
  p_llm_model_temperature INT,
  p_ai_agent_id VARCHAR(64), -- can be NULL, default is 'agent_translation_a1'
  p_translation_memory VARCHAR(256),
  p_translation_role TEXT,
  p_translation_rule TEXT,
  p_target_language VARCHAR(128),
  p_target_country VARCHAR(128),
  p_target_city VARCHAR(128), -- can be NULL
  p_task_type VARCHAR(32), -- can be NULL, default is 'localization'
  p_audience TEXT, -- can be NULL, default is 'general'
  p_purpose TEXT
)
RETURNS TABLE (
  status INT,
  message TEXT,
  file_preset_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_preset_count INT;
  v_file_preset_id UUID;
BEGIN

  -- Check if the preset with same description already exists for the principal
  /* v2026.01.22: Skipping this check for now to allow multiple presets with the same description
  SELECT COUNT(*) INTO v_preset_count
  FROM au_file_presets
  WHERE au_file_presets.principal_id = p_principal_id
    AND au_file_presets.description = p_description
    AND deleted_at IS NULL;

  IF v_preset_count > 0 THEN
    RETURN QUERY SELECT 409, 'Preset with same description already exists'::TEXT, NULL::UUID;
    RETURN;
  END IF;
  */

  -- Create the preset
  INSERT INTO au_file_presets (
    principal_id,
    description,
    llm_model_id,
    llm_model_temperature,
    ai_agent_id,
    translation_memory,
    translation_role,
    translation_rule,
    target_language,
    target_country,
    target_city,
    task_type,
    audience,
    purpose
  ) VALUES (
    p_principal_id,
    p_description,
    p_llm_model_id,
    p_llm_model_temperature,
    COALESCE(p_ai_agent_id, 'agent_translation_a1'),
    p_translation_memory,
    p_translation_role,
    p_translation_rule,
    p_target_language,
    p_target_country,
    p_target_city,
    COALESCE(p_task_type, 'localization'),
    COALESCE(p_audience, 'general'),
    p_purpose
  )
  RETURNING au_file_presets.file_preset_id INTO v_file_preset_id;

  -- Return result
  RETURN QUERY SELECT 200, 'File preset created successfully'::TEXT, v_file_preset_id;
END;
$$;


-- au_update_file_preset() function
CREATE OR REPLACE FUNCTION au_update_file_preset(
  p_file_preset_id UUID,
  p_description VARCHAR(128) DEFAULT NULL,
  p_llm_model_id VARCHAR(64) DEFAULT NULL,
  p_llm_model_temperature INT DEFAULT NULL,
  p_ai_agent_id VARCHAR(64) DEFAULT NULL,
  p_translation_memory VARCHAR(256) DEFAULT NULL,
  p_translation_role TEXT DEFAULT NULL,
  p_translation_rule TEXT DEFAULT NULL,
  p_target_language VARCHAR(128) DEFAULT NULL,
  p_target_country VARCHAR(128) DEFAULT NULL,
  p_target_city VARCHAR(128) DEFAULT NULL,
  p_task_type VARCHAR(32) DEFAULT NULL,
  p_audience TEXT DEFAULT NULL,
  p_purpose TEXT DEFAULT NULL
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_preset_count INT;
  v_principal_id UUID;
  v_updated BOOLEAN;
BEGIN

  -- Get principal_id of the preset
  SELECT principal_id INTO v_principal_id
  FROM au_file_presets
  WHERE au_file_presets.file_preset_id = p_file_preset_id
    AND deleted_at IS NULL;

  IF v_principal_id IS NULL THEN
    RETURN QUERY SELECT 404, 'File preset not found'::TEXT;
    RETURN;
  END IF;

  -- Update the preset
  UPDATE au_file_presets
  SET
    description = COALESCE(p_description, description),
    llm_model_id = COALESCE(p_llm_model_id, llm_model_id),
    llm_model_temperature = COALESCE(p_llm_model_temperature, llm_model_temperature),
    ai_agent_id = COALESCE(p_ai_agent_id, ai_agent_id),
    translation_memory = COALESCE(p_translation_memory, translation_memory),
    translation_role = COALESCE(p_translation_role, translation_role),
    translation_rule = COALESCE(p_translation_rule, translation_rule),
    target_language = COALESCE(p_target_language, target_language),
    target_country = COALESCE(p_target_country, target_country),
    target_city = COALESCE(p_target_city, target_city),
    task_type = COALESCE(p_task_type, task_type),
    audience = COALESCE(p_audience, audience),
    purpose = COALESCE(p_purpose, purpose),
    updated_at = now()
  WHERE au_file_presets.file_preset_id = p_file_preset_id
    AND deleted_at IS NULL;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'File preset updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File preset not found'::TEXT;
  END IF;
END;
$$;


-- au_delete_file_preset() function (soft delete)
CREATE OR REPLACE FUNCTION au_delete_file_preset(
  p_file_preset_id UUID
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

  -- Delete the preset (soft delete)
  UPDATE au_file_presets
  SET deleted_at = now()
  WHERE au_file_presets.file_preset_id = p_file_preset_id
    AND deleted_at IS NULL;

  -- Set v_deleted to TRUE if row was deleted, FALSE otherwise
  v_deleted := FOUND;

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'File preset deleted successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File preset not found'::TEXT;
  END IF;
END;
$$;


/*  au_get_file_preset() function

    Example usages:
    au_get_file_preset('principal-id');                   -- Get all presets for a principal
    au_get_file_preset('principal-id', 'preset-id');      -- Get specific preset  */
CREATE OR REPLACE FUNCTION au_get_file_preset(
  p_principal_id UUID,
  p_file_preset_id UUID DEFAULT NULL
)
RETURNS TABLE (
  file_preset_id UUID,
  principal_id UUID,
  description VARCHAR(128),
  llm_model_id VARCHAR(64),
  llm_model_temperature INT,
  ai_agent_id VARCHAR(64),
  translation_memory VARCHAR(256),
  translation_role TEXT,
  translation_rule TEXT,
  target_language VARCHAR(128),
  target_country VARCHAR(128),
  target_city VARCHAR(128),
  task_type VARCHAR(32),
  audience TEXT,
  purpose TEXT,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_file_preset_id IS NULL THEN
    -- Get all presets for the principal
    RETURN QUERY
    SELECT p.file_preset_id, p.principal_id, p.description,
           p.llm_model_id, p.llm_model_temperature, p.ai_agent_id,
           p.translation_memory, p.translation_role, p.translation_rule,
           p.target_language, p.target_country, p.target_city,
           p.task_type, p.audience, p.purpose, p.created_at, p.updated_at
    FROM au_file_presets p
    WHERE p.principal_id = p_principal_id
      AND p.deleted_at IS NULL
    ORDER BY p.updated_at DESC;
  ELSE
    -- Get specific preset
    RETURN QUERY
    SELECT p.file_preset_id, p.principal_id, p.description,
           p.llm_model_id, p.llm_model_temperature, p.ai_agent_id,
           p.translation_memory, p.translation_role, p.translation_rule,
           p.target_language, p.target_country, p.target_city,
           p.task_type, p.audience, p.purpose, p.created_at, p.updated_at
    FROM au_file_presets p
    WHERE p.principal_id = p_principal_id
      AND p.file_preset_id = p_file_preset_id
      AND p.deleted_at IS NULL;
  END IF;
END;
$$;
