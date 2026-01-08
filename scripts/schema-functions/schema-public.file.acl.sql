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


-- au_create_file_acl() function
CREATE OR REPLACE FUNCTION au_create_file_acl(
  p_file_id UUID,
  p_principal_id UUID,
  p_role VARCHAR(32) DEFAULT 'viewer'  -- 'viewer', 'editor', 'owner', 'viewer,downloadable', 'editor,downloadable', ... (one of 'viewer', 'editor', 'owner' and 'downloadable' can be combined)
)
RETURNS TABLE (
  status INT,
  message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_file_count INT;
  v_acl_count INT;
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

  -- Check if the ACL already exists
  SELECT COUNT(*) INTO v_acl_count
  FROM au_file_acl
  WHERE au_file_acl.file_id = p_file_id
    AND au_file_acl.principal_id = p_principal_id;

  IF v_acl_count > 0 THEN
    RETURN QUERY SELECT 409, 'ACL already exists for this principal'::TEXT;
    RETURN;
  END IF;

  -- Create the ACL
  INSERT INTO au_file_acl (
    file_id,
    principal_id,
    role
  ) VALUES (
    p_file_id,
    p_principal_id,
    p_role
  );

  -- Return result
  RETURN QUERY SELECT 200, 'File ACL created successfully'::TEXT;
END;
$$;


-- au_update_file_acl() function
CREATE OR REPLACE FUNCTION au_update_file_acl(
  p_file_id UUID,
  p_principal_id UUID,
  p_role VARCHAR(32)
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

  -- Update the ACL
  UPDATE au_file_acl
  SET
    role = p_role,
    updated_at = now()
  WHERE au_file_acl.file_id = p_file_id
    AND au_file_acl.principal_id = p_principal_id;

  -- Set v_updated to TRUE if row was updated, FALSE otherwise
  v_updated := FOUND;

  -- Return result
  IF v_updated THEN
    RETURN QUERY SELECT 200, 'File ACL updated successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File ACL not found'::TEXT;
  END IF;
END;
$$;


-- au_delete_file_acl() function
CREATE OR REPLACE FUNCTION au_delete_file_acl(
  p_file_id UUID,
  p_principal_id UUID
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

  -- Delete the ACL
  DELETE FROM au_file_acl
  WHERE au_file_acl.file_id = p_file_id
    AND au_file_acl.principal_id = p_principal_id;

  -- Set v_deleted to TRUE if row was deleted, FALSE otherwise
  v_deleted := FOUND;

  -- Return result
  IF v_deleted THEN
    RETURN QUERY SELECT 200, 'File ACL deleted successfully'::TEXT;
  ELSE
    RETURN QUERY SELECT 404, 'File ACL not found'::TEXT;
  END IF;
END;
$$;


/*  au_get_file_acl() function

    Example usages:
    au_get_file_acl('file-id');                        -- Get all ACLs for a file
    au_get_file_acl('file-id', 'principal-id');        -- Get specific ACL for a file and principal  */
CREATE OR REPLACE FUNCTION au_get_file_acl(
  p_file_id UUID,
  p_principal_id UUID DEFAULT NULL
)
RETURNS TABLE (
  file_id UUID,
  principal_id UUID,
  role VARCHAR(32),
  created_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  IF p_principal_id IS NULL THEN
    -- Get all ACLs for the file
    RETURN QUERY
    SELECT a.file_id, a.principal_id, a.role, a.created_at, a.updated_at
    FROM au_file_acl a
    WHERE a.file_id = p_file_id
    ORDER BY a.created_at ASC;
  ELSE
    -- Get specific ACL for file and principal
    RETURN QUERY
    SELECT a.file_id, a.principal_id, a.role, a.created_at, a.updated_at
    FROM au_file_acl a
    WHERE a.file_id = p_file_id
      AND a.principal_id = p_principal_id;
  END IF;
END;
$$;
