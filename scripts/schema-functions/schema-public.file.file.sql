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


-- au_create_file() function
CREATE OR REPLACE FUNCTION au_create_file(
  p_owner_id TEXT,
  p_parent_file_id UUID,
  p_file_type VARCHAR(32),
  p_file_name VARCHAR(512),
  p_file_url VARCHAR(1024),
  p_file_ext VARCHAR(32),
  p_file_size BIGINT,
  p_mime_type VARCHAR(32),
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
  v_file_count INT;
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

  -- Check if the file name already exists with the owner_id on the same parent folder
  SELECT COUNT(*) INTO v_file_count
  FROM au_file_nodes
  WHERE au_file_nodes.parent_file_id IS NOT DISTINCT FROM p_parent_file_id  -- Compare columns with NULL (NULL = NULL is TRUE)
    AND au_file_nodes.file_name = p_file_name
    AND owner_id = p_owner_id
    AND deleted_at IS NULL;

  IF v_file_count > 0 THEN
    RETURN QUERY SELECT 409, 'Folder/file name already exists'::TEXT, NULL::UUID;
    RETURN;
  END IF;

  -- Create the file
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
    p_file_type,
    p_file_name,
    p_file_url,
    COALESCE(p_file_ext, ''),
    COALESCE(p_file_size, 0),
    p_mime_type,
    p_description
  )
  RETURNING au_file_nodes.file_id INTO v_file_id;

  -- Return result
  RETURN QUERY SELECT 200, 'File created successfully'::TEXT, v_file_id;
END;
$$;


-- au_update_file() function
CREATE OR REPLACE FUNCTION au_update_file(
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
  v_file_count INT;
  v_updated BOOLEAN;
BEGIN

  -- Check if file_name already exists in the same parent folder
  IF p_file_name IS NOT NULL THEN
    SELECT COUNT(*) INTO v_file_count
    FROM au_file_nodes n
    WHERE n.parent_file_id IS NOT DISTINCT FROM (
        SELECT parent_file_id FROM au_file_nodes WHERE au_file_nodes.file_id = p_file_id
      )
      AND n.file_name = p_file_name
      AND n.file_id <> p_file_id
      AND n.deleted_at IS NULL;

    IF v_file_count > 0 THEN
      RETURN QUERY SELECT 409, 'Folder/file name already exists'::TEXT;
      RETURN;
    END IF;
  END IF;

  -- Update the file
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
    RETURN QUERY SELECT 200, 'File updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File not found'::TEXT;
  END IF;
END;
$$;


-- au_delete_file() function (soft delete)
CREATE OR REPLACE FUNCTION au_delete_file(
  p_file_id UUID
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

  -- Delete the file
  UPDATE au_file_nodes
  SET deleted_at = now()
  WHERE au_file_nodes.file_id = p_file_id
    AND deleted_at IS NULL;

  -- Set v_deleted to TRUE if row was deleted, FALSE otherwise
  v_deleted := FOUND;

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'File deleted successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File not found'::TEXT;
  END IF;
END;
$$;


-- au_duplicate_file() function (duplicate file in the same folder)
CREATE OR REPLACE FUNCTION au_duplicate_file(
  p_file_id UUID
)
RETURNS TABLE (
  status INT,
  message TEXT,
  file_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_owner_id TEXT;
  v_file_name VARCHAR(512);
  v_new_file_name VARCHAR(512);
  v_parent_file_id UUID;
  v_file_count INT;
  v_copy_count INT;
  v_new_file_id UUID;
BEGIN

  -- Get owner_id, file_name, and parent_file_id of the file to duplicate
  SELECT owner_id, file_name, parent_file_id INTO v_owner_id, v_file_name, v_parent_file_id
  FROM au_file_nodes
  WHERE au_file_nodes.file_id = p_file_id
    AND deleted_at IS NULL;

  IF v_owner_id IS NULL THEN
    RETURN QUERY SELECT 404, 'File not found'::TEXT, NULL::UUID;
    RETURN;
  END IF;

  -- Generate unique file name (append " (copy)" or " (copy N)")
  v_new_file_name := v_file_name || ' (copy)';
  v_copy_count := 1;

  LOOP
    SELECT COUNT(*) INTO v_file_count
    FROM au_file_nodes n
    WHERE n.parent_file_id IS NOT DISTINCT FROM v_parent_file_id
      AND n.file_name = v_new_file_name
      AND n.owner_id = v_owner_id
      AND n.deleted_at IS NULL;

    EXIT WHEN v_file_count = 0;

    v_copy_count := v_copy_count + 1;
    v_new_file_name := v_file_name || ' (copy ' || v_copy_count || ')';
  END LOOP;

  -- Duplicate the file
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
  )
  SELECT
    n.owner_id,
    n.parent_file_id,
    n.file_type,
    v_new_file_name,
    n.file_url,
    n.file_ext,
    n.file_size,
    n.mime_type,
    n.description
  FROM au_file_nodes n
  WHERE n.file_id = p_file_id
    AND n.deleted_at IS NULL
  RETURNING au_file_nodes.file_id INTO v_new_file_id;

  -- Return result
  RETURN QUERY SELECT 200, 'File duplicated successfully'::TEXT, v_new_file_id;
END;
$$;


-- au_move_file() function
CREATE OR REPLACE FUNCTION au_move_file(
  p_file_id UUID,
  p_new_parent_file_id UUID
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_owner_id TEXT;
  v_file_name VARCHAR(512);
  v_parent_count INT;
  v_file_count INT;
  v_updated BOOLEAN;
BEGIN

  -- Get owner_id and file_name of the file to move
  SELECT owner_id, file_name INTO v_owner_id, v_file_name
  FROM au_file_nodes
  WHERE au_file_nodes.file_id = p_file_id
    AND deleted_at IS NULL;

  IF v_owner_id IS NULL THEN
    RETURN QUERY SELECT 404, 'File not found'::TEXT;
    RETURN;
  END IF;

  -- Check if the new parent folder exists (skip for root level)
  IF p_new_parent_file_id IS NOT NULL THEN
    SELECT COUNT(*) INTO v_parent_count
    FROM au_file_nodes
    WHERE au_file_nodes.file_id = p_new_parent_file_id
      AND owner_id = v_owner_id
      AND deleted_at IS NULL;

    IF v_parent_count = 0 THEN
      RETURN QUERY SELECT 404, 'Parent folder not found'::TEXT;
      RETURN;
    END IF;
  END IF;

  -- Check if file name already exists in the new parent folder
  SELECT COUNT(*) INTO v_file_count
  FROM au_file_nodes n
  WHERE n.parent_file_id IS NOT DISTINCT FROM p_new_parent_file_id
    AND n.file_name = v_file_name
    AND n.owner_id = v_owner_id
    AND n.file_id <> p_file_id
    AND n.deleted_at IS NULL;

  IF v_file_count > 0 THEN
    RETURN QUERY SELECT 409, 'Folder/file name already exists'::TEXT;
    RETURN;
  END IF;

  -- Move the file
  UPDATE au_file_nodes
  SET
    parent_file_id = p_new_parent_file_id,
    updated_at = now()
  WHERE au_file_nodes.file_id = p_file_id
    AND deleted_at IS NULL;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'File moved successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File not found'::TEXT;
  END IF;
END;
$$;


/*  au_get_files() function

    Example usages:
    au_get_files('user-abc', 'all-files');           -- Get all my files
    au_get_files('user-abc', 'shared-files');        -- Get shared files
    au_get_files('user-abc', 'trash-files');         -- Get trash files (deleted files)
    au_get_files('user-abc', 'nodes');               -- Get root nodes
    au_get_files('user-abc', 'nodes', 'folder-id');  -- Get child nodes  */
CREATE OR REPLACE FUNCTION au_get_files(
  p_owner_id TEXT, 
  p_option VARCHAR(16) DEFAULT 'nodes',  -- 'all-files', 'shared-files', 'trash-files', 'nodes'
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
  IF p_option = 'all-files' THEN
    -- All files owned by user
    RETURN QUERY
    SELECT n.file_id, n.owner_id, n.parent_file_id, n.file_type,
           n.file_name, n.file_url, n.file_ext, n.file_size,
           n.mime_type, n.description, n.created_at, n.updated_at, n.deleted_at
    FROM au_file_nodes n
    WHERE n.owner_id = p_owner_id
      AND n.file_type = 'file'
      AND n.deleted_at IS NULL
    ORDER BY n.updated_at DESC;

  ELSIF p_option = 'shared-files' THEN
    -- Files shared with user
    RETURN QUERY
    SELECT n.file_id, n.owner_id, n.parent_file_id, n.file_type,
           n.file_name, n.file_url, n.file_ext, n.file_size,
           n.mime_type, n.description, n.created_at, n.updated_at, n.deleted_at
    FROM au_file_acl a
    INNER JOIN au_file_nodes n ON n.file_id = a.file_id
    WHERE a.principal_id = p_owner_id::UUID
      AND n.owner_id <> p_owner_id
      AND n.file_type = 'file'
      AND n.deleted_at IS NULL
    ORDER BY n.updated_at DESC;

  ELSIF p_option = 'trash-files' THEN
    -- Trash files owned by user (deleted files)
    RETURN QUERY
    SELECT n.file_id, n.owner_id, n.parent_file_id, n.file_type,
           n.file_name, n.file_url, n.file_ext, n.file_size,
           n.mime_type, n.description, n.created_at, n.updated_at, n.deleted_at
    FROM au_file_nodes n
    WHERE n.owner_id = p_owner_id
      AND n.file_type = 'file'
      AND n.deleted_at IS NOT NULL
    ORDER BY n.deleted_at DESC, n.file_name ASC;  -- Most recently deleted first

  ELSE  -- 'nodes' (default)
    -- Nodes at specific level (root or children) - owner's only
    RETURN QUERY
    SELECT n.file_id, n.owner_id, n.parent_file_id, n.file_type,
        n.file_name, n.file_url, n.file_ext, n.file_size,
        n.mime_type, n.description, n.created_at, n.updated_at, n.deleted_at
    FROM au_file_nodes n
    WHERE n.owner_id = p_owner_id
    AND n.parent_file_id IS NOT DISTINCT FROM p_parent_file_id  -- Compare columns with NULL (NULL = NULL is TRUE)
    AND n.deleted_at IS NULL
    ORDER BY n.file_type DESC, n.file_name ASC;  -- file_type: folder, file (folder first)
  END IF;  
END;
$$;


-- F_I1: For 'all-files' option (owner's files only)
-- Query: WHERE owner_id = ? ORDER BY updated_at DESC
CREATE INDEX IF NOT EXISTS idx_au_file_nodes_F_I1
    ON au_file_nodes
    (owner_id, updated_at DESC)
    WHERE deleted_at IS NULL AND file_type = 'file';

-- F_I2: For 'shared-files' option (joining with ACL)
-- Query: JOIN ON file_id, filter owner_id <>, ORDER BY updated_at DESC
CREATE INDEX IF NOT EXISTS idx_au_file_nodes_F_I2
    ON au_file_nodes
    (file_id)
    INCLUDE (owner_id, updated_at)
    WHERE deleted_at IS NULL AND file_type = 'file';

-- F_I3: For 'trash-files' option (deleted files)
-- Query: WHERE owner_id = ? ORDER BY deleted_at DESC, file_name ASC
CREATE INDEX IF NOT EXISTS idx_au_file_nodes_F_I3
    ON au_file_nodes
    (owner_id, deleted_at DESC, file_name ASC)
    WHERE deleted_at IS NOT NULL AND file_type = 'file';

-- F_I4: For 'nodes' option (owner's nodes at specific level)
-- Query: WHERE owner_id = ? AND parent_file_id IS NOT DISTINCT FROM ?
--        ORDER BY file_type DESC, file_name ASC
CREATE INDEX IF NOT EXISTS idx_au_file_nodes_F_I4
    ON au_file_nodes
    (owner_id, parent_file_id, file_type DESC, file_name ASC)
    WHERE deleted_at IS NULL;

-- F_I1: For 'shared-files' option (joining with au_file_nodes)
-- Query: WHERE a.principal_id = ?
--        JOIN au_file_nodes n ON n.file_id = a.file_id
CREATE INDEX IF NOT EXISTS idx_au_file_acl_F_I1
    ON au_file_acl
    (principal_id, file_id);
