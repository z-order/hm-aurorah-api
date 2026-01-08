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

-- Enable UUID generation (either pgcrypto or uuid-ossp)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- Crypto & random bytes
CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; -- UUIDv1–v5

/* uuid_generate_v7() function
   - RFC 9562–compliant UUID version 7
   - Single SELECT statement (no variables)
   - Implemented in SQL (not plpgsql)
   - 48-bit millisecond Unix timestamp (monotonic ordering)
   - Remaining bits are cryptographically random
   - Preserves RFC/IETF UUID variant bits
   - Converts a v4 UUID into v7 by setting version bits
   - PG 12–17 → use pg_uuidv7 or a SQL function like the one on the below
   - PG 18+ → use the built-in uuidv7() (faster, simpler, future-proof) */
CREATE OR REPLACE FUNCTION uuid_generate_v7() RETURNS uuid AS $$
  SELECT encode(                                    -- Convert binary to hex string
    set_bit(                                        -- Set variant bit (RFC 4122)
      set_bit(                                      -- Set version bit (UUIDv7)
        overlay(                                    -- Replace first 6 bytes with timestamp
          uuid_send(gen_random_uuid())              -- Generate random 16-byte UUID as base
          placing substring(                        -- Extract 6 bytes (48 bits) for timestamp
            int8send(                               -- Convert bigint to 8-byte binary
              floor(                                -- Remove fractional milliseconds
                extract(epoch from clock_timestamp()) * 1000  -- Get Unix timestamp in milliseconds
              )::bigint
            ) from 3                                -- Skip first 2 bytes, take last 6 bytes
          )
          from 1 for 6                              -- Replace bytes 1-6 with timestamp
        ),
        52, 1                                       -- Set bit 52 to 1 (version field)
      ),
      53, 1                                         -- Set bit 53 to 1 (variant field)
    ),
    'hex'                                           -- Encode as hexadecimal string
  )::uuid;                                          -- Cast to UUID type
$$ LANGUAGE sql VOLATILE;
