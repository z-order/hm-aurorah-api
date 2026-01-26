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


-- au_create_file_edit_history() function
CREATE OR REPLACE FUNCTION au_create_file_edit_history(
  p_file_id UUID,
  p_target_type VARCHAR(32),
  p_target_id UUID,
  p_marker_number INT,
  p_editor_id UUID,
  p_text_before TEXT,
  p_text_after TEXT,
  p_comments TEXT DEFAULT NULL
)
RETURNS TABLE (
  status INT,
  message TEXT,
  history_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_history_id UUID;
  v_last_checkpoint_at TIMESTAMPTZ;
  v_original_text_modified JSONB;
  v_translated_text_modified JSONB;
  v_proofreaded_text JSONB;
BEGIN

  -- Create the edit history (FK constraint will validate file_id)
  INSERT INTO au_file_edit_history (
    file_id,
    target_type,
    target_id,
    marker_number,
    editor_id,
    text_before,
    text_after,
    comments
  ) VALUES (
    p_file_id,
    p_target_type,
    p_target_id,
    p_marker_number,
    p_editor_id,
    p_text_before,
    p_text_after,
    p_comments
  )
  RETURNING au_file_edit_history.history_id INTO v_history_id;

  -- Check if checkpoint exists within last 20 minutes (optimized: uses LIMIT 1 instead of MAX)
  SELECT c.created_at INTO v_last_checkpoint_at
  FROM au_file_checkpoint c
  WHERE c.file_id = p_file_id
    AND c.created_at > now() - INTERVAL '20 minutes'
  ORDER BY c.created_at DESC
  LIMIT 1;

  -- Create checkpoint if no recent checkpoint exists
  IF v_last_checkpoint_at IS NULL THEN
    -- Get current modified texts from related tables in a single query
    SELECT o.original_text_modified, t.translated_text_modified, pr.proofreaded_text
    INTO v_original_text_modified, v_translated_text_modified, v_proofreaded_text
    FROM au_file_tasks tk
    LEFT JOIN au_file_original o ON o.original_id = tk.original_id
    LEFT JOIN au_file_translation t ON t.translation_id = tk.translation_id_1st
    LEFT JOIN au_file_proofreading pr ON pr.proofreading_id = tk.proofreading_id
    WHERE tk.file_id = p_file_id;

    -- Create checkpoint
    PERFORM au_create_file_checkpoint(
      p_file_id,
      v_history_id,
      v_original_text_modified,
      v_translated_text_modified,
      v_proofreaded_text
    );
  END IF;

  -- Return result
  RETURN QUERY SELECT 200, 'File edit history created successfully'::TEXT, v_history_id;
END;
$$;


/*  au_get_file_edit_history() function

    Example usages:
    au_get_file_edit_history('file-id');                                      -- Get all edit history for a file
    au_get_file_edit_history('file-id', 'original');                          -- Get edit history by target_type
    au_get_file_edit_history('file-id', 'original', 'target-id');             -- Get edit history by target_type and target_id
    au_get_file_edit_history('file-id', 'original', 'target-id', 1);          -- Get edit history by target_type, target_id, and marker_number  */
CREATE OR REPLACE FUNCTION au_get_file_edit_history(
  p_file_id UUID,
  p_target_type VARCHAR(32) DEFAULT NULL,
  p_target_id UUID DEFAULT NULL,
  p_marker_number INT DEFAULT NULL
)
RETURNS TABLE (
  history_id UUID,
  file_id UUID,
  target_type VARCHAR(32),
  target_id UUID,
  marker_number INT,
  editor_id UUID,
  text_before TEXT,
  text_after TEXT,
  comments TEXT,
  created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT h.history_id, h.file_id, h.target_type, h.target_id, h.marker_number,
         h.editor_id, h.text_before, h.text_after, h.comments, h.created_at
  FROM au_file_edit_history h
  WHERE h.file_id = p_file_id
    AND (p_target_type IS NULL OR h.target_type = p_target_type)
    AND (p_target_id IS NULL OR h.target_id = p_target_id)
    AND (p_marker_number IS NULL OR h.marker_number = p_marker_number)
  ORDER BY h.created_at DESC;
END;
$$;
