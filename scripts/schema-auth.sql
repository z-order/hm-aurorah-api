/*
   -- Auth.js PostgreSQL Schema for hm-aurorah-web @auth/pg-adapter
   -- Ref for database schema: https://authjs.dev/getting-started/database, https://authjs.dev/concepts/database-models
   -- Run this SQL to create required tables 

   Option 1: Using environment from .env.local
   $ psql $POSTGRES_URL < schema.sql
  
   Option 2: Using psql command line
   $ psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME -f schema.sql
  
   Option 3: Manually connect and execute:
   $ psql postgresql://your_user:your_password@your_host/your_database < schema.sql
  
   Verify tables were created:
   $ psql $POSTGRES_URL -c "\dt"
*/

CREATE SCHEMA auth;

-- Enable UUID generation (either pgcrypto or uuid-ossp)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS auth.accounts (
  id TEXT NOT NULL DEFAULT gen_random_uuid(),
  "userId" TEXT NOT NULL,
  type VARCHAR(255) NOT NULL,
  provider VARCHAR(255) NOT NULL,
  "providerAccountId" VARCHAR(255) NOT NULL,
  refresh_token TEXT,
  access_token TEXT,
  expires_at BIGINT,
  id_token TEXT,
  scope TEXT,
  session_state TEXT,
  token_type TEXT,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS auth.users (
  id TEXT NOT NULL DEFAULT gen_random_uuid(),
  name VARCHAR(255),
  email VARCHAR(255) UNIQUE,
  "emailVerified" TIMESTAMPTZ,
  image TEXT,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS auth.sessions (
  id TEXT NOT NULL DEFAULT gen_random_uuid(),
  "userId" TEXT NOT NULL,
  "sessionToken" TEXT NOT NULL UNIQUE,
  expires TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS auth.verification_token (
  identifier TEXT NOT NULL,
  token TEXT NOT NULL,
  expires TIMESTAMPTZ NOT NULL,
  PRIMARY KEY (identifier, token)
);

ALTER TABLE auth.accounts ADD CONSTRAINT fk_user_accounts FOREIGN KEY ("userId") REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE auth.sessions ADD CONSTRAINT fk_user_sessions FOREIGN KEY ("userId") REFERENCES auth.users(id) ON DELETE CASCADE;

-- Indices for optimized queries
CREATE INDEX IF NOT EXISTS idx_accounts_userId ON auth.accounts("userId");
CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_provider_providerAccountId ON auth.accounts(provider, "providerAccountId");
CREATE INDEX IF NOT EXISTS idx_sessions_userId ON auth.sessions("userId");
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON auth.sessions(expires);
CREATE INDEX IF NOT EXISTS idx_verification_token_token ON auth.verification_token(token);
CREATE INDEX IF NOT EXISTS idx_verification_token_expires ON auth.verification_token(expires);
