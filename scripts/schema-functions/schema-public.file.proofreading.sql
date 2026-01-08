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


-- au_create_file_proofreading() function
CREATE OR REPLACE FUNCTION au_create_file_proofreading(
  p_file_id UUID,
  p_assignee_id UUID,
  p_participant_ids UUID[],
  p_proofreaded_text JSONB
)
RETURNS TABLE (
  status INT,
  message TEXT,
  proofreading_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_file_count INT;
  v_proofreading_id UUID;
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

  -- Create the proofreading
  INSERT INTO au_file_proofreading (
    file_id,
    assignee_id,
    participant_ids,
    proofreaded_text
  ) VALUES (
    p_file_id,
    p_assignee_id,
    p_participant_ids,
    p_proofreaded_text
  )
  RETURNING au_file_proofreading.proofreading_id INTO v_proofreading_id;

  -- Return result
  RETURN QUERY SELECT 200, 'File proofreading created successfully'::TEXT, v_proofreading_id;
END;
$$;


-- au_update_file_proofreading() function
CREATE OR REPLACE FUNCTION au_update_file_proofreading(
  p_proofreading_id UUID,
  p_assignee_id UUID DEFAULT NULL,
  p_participant_ids UUID[] DEFAULT NULL,
  p_proofreaded_text JSONB DEFAULT NULL
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

  -- Update the proofreading
  UPDATE au_file_proofreading
  SET
    assignee_id = COALESCE(p_assignee_id, assignee_id),
    participant_ids = COALESCE(p_participant_ids, participant_ids),
    proofreaded_text = COALESCE(p_proofreaded_text, proofreaded_text),
    updated_at = now()
  WHERE au_file_proofreading.proofreading_id = p_proofreading_id
    AND deleted_at IS NULL;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'File proofreading updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File proofreading not found'::TEXT;
  END IF;
END;
$$;


-- au_delete_file_proofreading() function (soft delete)
CREATE OR REPLACE FUNCTION au_delete_file_proofreading(
  p_proofreading_id UUID
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

  -- Delete the proofreading (soft delete)
  UPDATE au_file_proofreading
  SET deleted_at = now()
  WHERE au_file_proofreading.proofreading_id = p_proofreading_id
    AND deleted_at IS NULL;

  -- Set v_deleted to TRUE if row was deleted, FALSE otherwise
  v_deleted := FOUND;

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'File proofreading deleted successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File proofreading not found'::TEXT;
  END IF;
END;
$$;


/*  au_get_file_proofreading_for_listing() function

    Example usages:
    au_get_file_proofreading_for_listing('file-id');                        -- Get all proofreadings for a file
    au_get_file_proofreading_for_listing('file-id', 'proofreading-id');     -- Get specific proofreading  */
CREATE OR REPLACE FUNCTION au_get_file_proofreading_for_listing(
  p_file_id UUID,
  p_proofreading_id UUID DEFAULT NULL
)
RETURNS TABLE (
  proofreading_id UUID,
  file_id UUID,
  assignee_id UUID,
  participant_ids UUID[],
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_proofreading_id IS NULL THEN
    -- Get all proofreadings for the file
    RETURN QUERY
    SELECT p.proofreading_id, p.file_id, p.assignee_id, p.participant_ids,
           p.created_at, p.updated_at
    FROM au_file_proofreading p
    WHERE p.file_id = p_file_id
      AND p.deleted_at IS NULL
    ORDER BY p.created_at DESC;
  ELSE
    -- Get specific proofreading
    RETURN QUERY
    SELECT p.proofreading_id, p.file_id, p.assignee_id, p.participant_ids,
           p.created_at, p.updated_at
    FROM au_file_proofreading p
    WHERE p.file_id = p_file_id
      AND p.proofreading_id = p_proofreading_id
      AND p.deleted_at IS NULL;
  END IF;
END;
$$;


/*  au_get_file_proofreading_for_jsonb() function

    Example usages:
    au_get_file_proofreading_for_jsonb('file-id');                          -- Get all proofreadings for a file
    au_get_file_proofreading_for_jsonb('file-id', 'proofreading-id');       -- Get specific proofreading  */
CREATE OR REPLACE FUNCTION au_get_file_proofreading_for_jsonb(
  p_file_id UUID,
  p_proofreading_id UUID DEFAULT NULL
)
RETURNS TABLE (
  proofreading_id UUID,
  file_id UUID,
  assignee_id UUID,
  participant_ids UUID[],
  proofreaded_text JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_proofreading_id IS NULL THEN
    -- Get all proofreadings for the file
    RETURN QUERY
    SELECT p.proofreading_id, p.file_id, p.assignee_id, p.participant_ids,
           p.proofreaded_text, p.created_at, p.updated_at
    FROM au_file_proofreading p
    WHERE p.file_id = p_file_id
      AND p.deleted_at IS NULL
    ORDER BY p.created_at DESC;
  ELSE
    -- Get specific proofreading
    RETURN QUERY
    SELECT p.proofreading_id, p.file_id, p.assignee_id, p.participant_ids,
           p.proofreaded_text, p.created_at, p.updated_at
    FROM au_file_proofreading p
    WHERE p.file_id = p_file_id
      AND p.proofreading_id = p_proofreading_id
      AND p.deleted_at IS NULL;
  END IF;
END;
$$;
