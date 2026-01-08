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


-- au_create_file_original() function
CREATE OR REPLACE FUNCTION au_create_file_original(
  p_file_id UUID,
  p_original_text JSONB
)
RETURNS TABLE (
  status INT,
  message TEXT,
  original_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_file_count INT;
  v_original_count INT;
  v_original_id UUID;
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

  -- Check if original already exists for this file
  SELECT COUNT(*) INTO v_original_count
  FROM au_file_original
  WHERE au_file_original.file_id = p_file_id;

  IF v_original_count > 0 THEN
    RETURN QUERY SELECT 409, 'Original text already exists for this file'::TEXT, NULL::UUID;
    RETURN;
  END IF;

  -- Create the original
  INSERT INTO au_file_original (
    file_id,
    original_text
  ) VALUES (
    p_file_id,
    p_original_text
  )
  RETURNING au_file_original.original_id INTO v_original_id;

  -- Return result
  RETURN QUERY SELECT 200, 'File original created successfully'::TEXT, v_original_id;
END;
$$;


-- au_update_file_original() function
CREATE OR REPLACE FUNCTION au_update_file_original(
  p_original_id UUID,
  p_original_text JSONB DEFAULT NULL,
  p_original_text_modified JSONB DEFAULT NULL
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

  -- Update the original
  UPDATE au_file_original
  SET
    original_text = COALESCE(p_original_text, original_text),
    original_text_modified = COALESCE(p_original_text_modified, original_text_modified),
    updated_at = now()
  WHERE au_file_original.original_id = p_original_id;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'File original updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File original not found'::TEXT;
  END IF;
END;
$$;


/*  au_get_file_original() function

    Example usages:
    au_get_file_original('file-id');                   -- Get original by file_id
    au_get_file_original(NULL, 'original-id');         -- Get original by original_id  */
CREATE OR REPLACE FUNCTION au_get_file_original(
  p_file_id UUID DEFAULT NULL,
  p_original_id UUID DEFAULT NULL
)
RETURNS TABLE (
  original_id UUID,
  file_id UUID,
  original_text JSONB,
  original_text_modified JSONB,
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_original_id IS NOT NULL THEN
    -- Get by original_id
    RETURN QUERY
    SELECT o.original_id, o.file_id, o.original_text, o.original_text_modified,
           o.created_at, o.updated_at
    FROM au_file_original o
    WHERE o.original_id = p_original_id;
  ELSIF p_file_id IS NOT NULL THEN
    -- Get by file_id
    RETURN QUERY
    SELECT o.original_id, o.file_id, o.original_text, o.original_text_modified,
           o.created_at, o.updated_at
    FROM au_file_original o
    WHERE o.file_id = p_file_id;
  END IF;
END;
$$;
