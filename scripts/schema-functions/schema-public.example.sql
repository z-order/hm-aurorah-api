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


-- Function Example using PL/pgSQL
CREATE OR REPLACE FUNCTION au_ex_get_files1(p_owner_id TEXT)
RETURNS TABLE (
    owner_id TEXT,
    file_id TEXT,
    file_name TEXT,
    file_type TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT * FROM (
        SELECT p_owner_id, 'file_id1'::TEXT, 'file_name1'::TEXT, 'file_type1'::TEXT
        UNION ALL
        SELECT p_owner_id, 'file_id2'::TEXT, 'file_name2'::TEXT, 'file_type2'::TEXT
    ) AS files(owner_id, file_id, file_name, file_type);
END;
$$;


-- Function Example using SQL
CREATE OR REPLACE FUNCTION au_ex_get_files2(p_owner_id TEXT)
RETURNS TABLE (
    owner_id TEXT,
    file_id TEXT,
    file_name TEXT,
    file_type TEXT
)
LANGUAGE sql
AS $$
    SELECT p_owner_id, 'file_id1'::TEXT, 'file_name1'::TEXT, 'file_type1'::TEXT
    UNION ALL
    SELECT p_owner_id, 'file_id2'::TEXT, 'file_name2'::TEXT, 'file_type2'::TEXT;
$$;
