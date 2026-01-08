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


-- au_create_folder() function
CREATE OR REPLACE FUNCTION au_create_folder(
  p_owner_id TEXT,
  p_parent_file_id UUID,
  p_file_name VARCHAR(512),
  p_description VARCHAR(512)
)
RETURNS TABLE (
  status INT,
  message TEXT,
  file_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_parent_count INT;
  v_folder_count INT;
  v_file_id UUID;
BEGIN

  -- Check if the parent folder exists (skip for root level)
  IF p_parent_file_id IS NOT NULL THEN
    SELECT COUNT(*) INTO v_parent_count
    FROM au_file_nodes
    WHERE au_file_nodes.file_id = p_parent_file_id
      AND owner_id = p_owner_id
      AND deleted_at IS NULL;

    IF v_parent_count = 0 THEN
      RETURN QUERY SELECT 404, 'Parent folder not found'::TEXT, NULL::UUID;
      RETURN;
    END IF;
  END IF;

  -- Check if the folder name already exists with the owner_id on the same parent folder
  SELECT COUNT(*) INTO v_folder_count
  FROM au_file_nodes
  WHERE au_file_nodes.parent_file_id IS NOT DISTINCT FROM p_parent_file_id  -- Compare columns with NULL (NULL = NULL is TRUE)
    AND au_file_nodes.file_name = p_file_name
    AND owner_id = p_owner_id
    AND deleted_at IS NULL;

  IF v_folder_count > 0 THEN
    RETURN QUERY SELECT 409, 'Folder/file name already exists'::TEXT, NULL::UUID;
    RETURN;
  END IF;

  -- Create the folder
  INSERT INTO au_file_nodes (
    owner_id,
    parent_file_id,
    file_type,
    file_name,
    file_url,
    file_ext,
    file_size,
    mime_type,
    description
  ) VALUES (
    p_owner_id,
    p_parent_file_id,
    'folder',
    p_file_name,
    NULL,
    '',
    0,
    NULL,
    p_description
  )
  RETURNING au_file_nodes.file_id INTO v_file_id;

  -- Return result
  RETURN QUERY SELECT 200, 'Folder created successfully'::TEXT, v_file_id;
END;
$$;


-- au_update_folder() function
CREATE OR REPLACE FUNCTION au_update_folder(
  p_file_id UUID,
  p_file_name VARCHAR(512) DEFAULT NULL,
  p_description VARCHAR(512) DEFAULT NULL
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_folder_count INT;
  v_updated BOOLEAN;
BEGIN

  -- Check if file_name already exists in the same parent folder
  IF p_file_name IS NOT NULL THEN
    SELECT COUNT(*) INTO v_folder_count
    FROM au_file_nodes n
    WHERE n.parent_file_id IS NOT DISTINCT FROM (
        SELECT parent_file_id FROM au_file_nodes WHERE au_file_nodes.file_id = p_file_id
      )
      AND n.file_name = p_file_name
      AND n.file_id <> p_file_id
      AND n.deleted_at IS NULL;

    IF v_folder_count > 0 THEN
      RETURN QUERY SELECT 409, 'Folder/file name already exists'::TEXT;
      RETURN;
    END IF;
  END IF;

  -- Update the folder
  UPDATE au_file_nodes
  SET
    file_name = COALESCE(p_file_name, file_name),
    description = COALESCE(p_description, description),
    updated_at = now()
  WHERE au_file_nodes.file_id = p_file_id
    AND deleted_at IS NULL;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'Folder updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'Folder not found'::TEXT;
  END IF;
END;
$$;


-- au_delete_folder() function (checks if folder is empty)
CREATE OR REPLACE FUNCTION au_delete_folder(
  p_file_id UUID
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_child_count INT;
  v_deleted BOOLEAN;
BEGIN
  -- Check if folder has children
  SELECT COUNT(*) INTO v_child_count
  FROM au_file_nodes
  WHERE parent_file_id = p_file_id
    AND deleted_at IS NULL;

  IF v_child_count > 0 THEN
    RETURN QUERY SELECT 409, 'Folder is not empty';
    RETURN;
  END IF;

  -- Delete the folder
  v_deleted := au_delete_file(p_file_id);

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'Folder deleted successfully';
  ELSE
    RETURN QUERY SELECT 404, 'Folder not found';
  END IF;
END;
$$;


-- au_get_folders() function (alias of au_get_files)
CREATE OR REPLACE FUNCTION au_get_folders(
  p_owner_id TEXT,
  p_option VARCHAR(16) DEFAULT 'nodes',
  p_parent_file_id UUID DEFAULT NULL
)
RETURNS TABLE (
  file_id UUID,
  owner_id TEXT,
  parent_file_id UUID,
  file_type VARCHAR(32),
  file_name VARCHAR(512),
  file_url VARCHAR(1024),
  file_ext VARCHAR(32),
  file_size BIGINT,
  mime_type VARCHAR(32),
  description VARCHAR(512),
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY SELECT * FROM au_get_files(p_owner_id, p_option, p_parent_file_id);
END;
$$;
