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


-- au_create_file_task() function
CREATE OR REPLACE FUNCTION au_create_file_task(
  p_file_id UUID,
  p_file_preset_id UUID,
  p_original_text JSONB
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_file_count INT;
  v_task_count INT;
  v_original_status INT;
  v_original_message TEXT;
  v_original_id UUID;
BEGIN

  -- Check if the file exists
  SELECT COUNT(*) INTO v_file_count
  FROM au_file_nodes
  WHERE au_file_nodes.file_id = p_file_id
    AND deleted_at IS NULL;

  IF v_file_count = 0 THEN
    RETURN QUERY SELECT 404, 'File not found'::TEXT;
    RETURN;
  END IF;

  -- Check if task already exists for this file (1:1 relationship)
  SELECT COUNT(*) INTO v_task_count
  FROM au_file_tasks
  WHERE au_file_tasks.file_id = p_file_id;

  IF v_task_count > 0 THEN
    RETURN QUERY SELECT 409, 'Task already exists for this file'::TEXT;
    RETURN;
  END IF;

  -- Create the original record
  SELECT r.status, r.message, r.original_id INTO v_original_status, v_original_message, v_original_id
  FROM au_create_file_original(p_file_id, p_original_text) r;

  IF v_original_status <> 200 THEN
    RETURN QUERY SELECT v_original_status, v_original_message;
    RETURN;
  END IF;

  -- Create the task
  INSERT INTO au_file_tasks (
    file_id,
    file_preset_id,
    original_id
  ) VALUES (
    p_file_id,
    p_file_preset_id,
    v_original_id
  );

  -- Return result
  RETURN QUERY SELECT 200, 'File task created successfully'::TEXT;
END;
$$;


-- au_update_file_task() function
CREATE OR REPLACE FUNCTION au_update_file_task(
  p_file_id UUID,
  p_file_preset_id UUID DEFAULT NULL,
  p_translation_id_1st UUID DEFAULT NULL,
  p_translation_id_2nd UUID DEFAULT NULL,
  p_proofreading_id UUID DEFAULT NULL
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

  -- Update the task
  UPDATE au_file_tasks
  SET
    file_preset_id = COALESCE(p_file_preset_id, file_preset_id),
    translation_id_1st = COALESCE(p_translation_id_1st, translation_id_1st),
    translation_id_2nd = COALESCE(p_translation_id_2nd, translation_id_2nd),
    proofreading_id = COALESCE(p_proofreading_id, proofreading_id),
    updated_at = now()
  WHERE au_file_tasks.file_id = p_file_id;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'File task updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File task not found'::TEXT;
  END IF;
END;
$$;


/*  au_get_file_task() function

    Example usages:
    au_get_file_task('file-id');     -- Get task for a file  */
CREATE OR REPLACE FUNCTION au_get_file_task(
  p_file_id UUID
)
RETURNS TABLE (
  file_id UUID,
  file_preset_id UUID,
  original_id UUID,
  translation_id_1st UUID,
  translation_id_2nd UUID,
  proofreading_id UUID,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT t.file_id, t.file_preset_id, t.original_id,
         t.translation_id_1st, t.translation_id_2nd, t.proofreading_id,
         t.created_at, t.updated_at
  FROM au_file_tasks t
  WHERE t.file_id = p_file_id;
END;
$$;


/*  au_get_file_task_with_details() function

    Example usages:
    au_get_file_task_with_details('file-id');     -- Get task with related details  */
CREATE OR REPLACE FUNCTION au_get_file_task_with_details(
  p_file_id UUID
)
RETURNS TABLE (
  file_id UUID,
  file_preset_id UUID,
  original_id UUID,
  original_text JSONB,
  original_text_modified JSONB,
  translation_id_1st UUID,
  translation_id_2nd UUID,
  proofreading_id UUID,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT t.file_id, t.file_preset_id, t.original_id,
         o.original_text, o.original_text_modified,
         t.translation_id_1st, t.translation_id_2nd, t.proofreading_id,
         t.created_at, t.updated_at
  FROM au_file_tasks t
  LEFT JOIN au_file_original o ON o.original_id = t.original_id
  WHERE t.file_id = p_file_id;
END;
$$;
