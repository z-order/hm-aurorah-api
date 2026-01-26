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


-- au_create_file_checkpoint() function
CREATE OR REPLACE FUNCTION au_create_file_checkpoint(
  p_file_id UUID,
  p_history_id UUID,
  p_original_text_modified JSONB DEFAULT NULL,
  p_translated_text_modified JSONB DEFAULT NULL,
  p_proofreaded_text JSONB DEFAULT NULL
)
RETURNS TABLE (
  status INT,
  message TEXT,
  checkpoint_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_file_count INT;
  v_history_count INT;
  v_checkpoint_id UUID;
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

  -- Check if the history exists
  SELECT COUNT(*) INTO v_history_count
  FROM au_file_edit_history
  WHERE au_file_edit_history.history_id = p_history_id;

  IF v_history_count = 0 THEN
    RETURN QUERY SELECT 404, 'Edit history not found'::TEXT, NULL::UUID;
    RETURN;
  END IF;

  -- Create the checkpoint
  INSERT INTO au_file_checkpoint (
    file_id,
    history_id,
    original_text_modified,
    translated_text_modified,
    proofreaded_text
  ) VALUES (
    p_file_id,
    p_history_id,
    p_original_text_modified,
    p_translated_text_modified,
    p_proofreaded_text
  )
  RETURNING au_file_checkpoint.checkpoint_id INTO v_checkpoint_id;

  -- Return result
  RETURN QUERY SELECT 200, 'File checkpoint created successfully'::TEXT, v_checkpoint_id;
END;
$$;


/*  au_get_file_checkpoint() function

    Example usages:
    au_get_file_checkpoint('file-id');                       -- Get all checkpoints for a file
    au_get_file_checkpoint('file-id', 'checkpoint-id');      -- Get specific checkpoint  */
CREATE OR REPLACE FUNCTION au_get_file_checkpoint(
  p_file_id UUID,
  p_checkpoint_id UUID DEFAULT NULL
)
RETURNS TABLE (
  checkpoint_id UUID,
  file_id UUID,
  history_id UUID,
  original_text_modified JSONB,
  translated_text_modified JSONB,
  proofreaded_text JSONB,
  created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_checkpoint_id IS NULL THEN
    -- Get all checkpoints for the file
    RETURN QUERY
    SELECT c.checkpoint_id, c.file_id, c.history_id,
           c.original_text_modified, c.translated_text_modified, c.proofreaded_text,
           c.created_at
    FROM au_file_checkpoint c
    WHERE c.file_id = p_file_id
    ORDER BY c.created_at DESC;
  ELSE
    -- Get specific checkpoint
    RETURN QUERY
    SELECT c.checkpoint_id, c.file_id, c.history_id,
           c.original_text_modified, c.translated_text_modified, c.proofreaded_text,
           c.created_at
    FROM au_file_checkpoint c
    WHERE c.file_id = p_file_id
      AND c.checkpoint_id = p_checkpoint_id;
  END IF;
END;
$$;
