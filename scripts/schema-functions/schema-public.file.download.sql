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


/*  au_get_file_translation_for_download() function

    Returns translated_text and translated_text_modified JSONB columns
    for the file download feature. Looks up by translation_id only
    (does not require file_id).

    Example usage:
    au_get_file_translation_for_download('translation-id');  */
CREATE OR REPLACE FUNCTION au_get_file_translation_for_download(
  p_translation_id UUID
)
RETURNS TABLE (
  translated_text JSONB,
  translated_text_modified JSONB
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT t.translated_text, t.translated_text_modified
  FROM au_file_translation t
  WHERE t.translation_id = p_translation_id
    AND t.deleted_at IS NULL;
END;
$$;


/*  au_get_file_proofreading_for_download() function

    Returns proofreaded_text JSONB column for the file download feature.
    Looks up by proofreading_id only (does not require file_id).

    Note: proofreaded_text_modified column is planned but not yet added.
    When added, update this function to also return it.

    Example usage:
    au_get_file_proofreading_for_download('proofreading-id');  */
CREATE OR REPLACE FUNCTION au_get_file_proofreading_for_download(
  p_proofreading_id UUID
)
RETURNS TABLE (
  proofreaded_text JSONB,
  proofreaded_text_modified JSONB
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT p.proofreaded_text, NULL::JSONB AS proofreaded_text_modified
  FROM au_file_proofreading p
  WHERE p.proofreading_id = p_proofreading_id
    AND p.deleted_at IS NULL;
END;
$$;
