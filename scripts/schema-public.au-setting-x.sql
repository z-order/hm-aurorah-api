/*
   -- Run this SQL to create required au_setting_* tables 

   Option 1: Using environment from .env.local
   $ psql $POSTGRES_URL < schema.sql
  
   Option 2: Using psql command line
   $ psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -f schema.sql
  
   Option 3: Manually connect and execute:
   $ psql postgresql://your_user:your_password@your_host/your_database < schema.sql
  
   Verify tables were created:
   $ psql $POSTGRES_URL -c "\dt"
*/

CREATE SCHEMA IF NOT EXISTS public;
SET search_path TO public;

-- Enable UUID generation (either pgcrypto or uuid-ossp)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- Crypto & random bytes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- UUIDv1–v5
