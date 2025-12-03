#!/bin/sh

show_help() {
    cat << 'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                       POSTGRESQL CLI HELPER SCRIPT                         ║
╚════════════════════════════════════════════════════════════════════════════╝

USAGE:
  ./postgres.sh              Connect to PostgreSQL using POSTGRES_URL environment variable
  ./postgres.sh --help       Show this help message

ALTERNATIVE CONNECTION:
  psql -h localhost -p 5432 -U username -d database

╔════════════════════════════════════════════════════════════════════════════╗
║                            QUICK COMMANDS                                  ║
╚════════════════════════════════════════════════════════════════════════════╝
 
  Help:
    \?                            Show all psql commands
    \h                            Show SQL command help
    \h <command>                  Show help for specific SQL command

  Database Navigation:
    \l                            List all databases
    \l+                           List all databases with details
    \c database_name              Connect to a database
    \c database_name username     Connect to database as specific user

  Schema Navigation:
    \dn                           List all schemas
    \dn+                          List all schemas with details
    SHOW search_path;             Show current search path
    SET search_path TO schema;    Switch to a schema

  Table Operations:
    \dt                           List all tables in current schema
    \dt+                          List all tables with details
    \dt schema_name.*             List tables in specific schema
    \d table_name                 Describe table structure
    \d+ table_name                Describe table with full details

  View Operations:
    \dv                           List all views
    \dv+                          List all views with details

  Index Operations:
    \di                           List all indexes
    \di+                          List all indexes with details

  Sequence Operations:
    \ds                           List all sequences
    \ds+                          List all sequences with details

  Function Operations:
    \df                           List all functions
    \df+                          List all functions with details

  User & Role Management:
    \du                           List all users/roles
    \du+                          List all users/roles with details

  Display Settings:
    \x                            Toggle expanded display (good for wide tables)
    \x auto                       Auto expanded display
    \timing                       Toggle query execution time display

  Query Execution:
    \i filename.sql               Execute SQL from file
    \o filename.txt               Save query output to file
    \o                            Stop saving output to file

  System Info:
    SELECT version();             Show PostgreSQL version
    \conninfo                     Show connection information
    \timing on                    Show query execution time

  Exit:
    \q                            Quit psql

╔════════════════════════════════════════════════════════════════════════════╗
║                    BASIC POSTGRESQL COMMANDS REFERENCE                     ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─ CONNECTION & SERVER ──────────────────────────────────────────────────────┐
│ psql -h host -p port -U user -d db  Connect to PostgreSQL                  │
│ \c database                         Switch database                        │
│ \conninfo                           Show connection info                   │
│ \q                                  Quit psql                              │
│ SELECT version();                   Show PostgreSQL version                │
│ SELECT current_database();          Show current database                  │
│ SELECT current_schema();            Show current schema                    │
└────────────────────────────────────────────────────────────────────────────┘

┌─ DATABASE OPERATIONS ──────────────────────────────────────────────────────┐
│ CREATE DATABASE dbname;             Create new database                    │
│ DROP DATABASE dbname;               Delete database                        │
│ \l                                  List all databases                     │
│ \l+                                 List databases with size/description   │
│ ALTER DATABASE dbname RENAME TO new; Rename database                       │
└────────────────────────────────────────────────────────────────────────────┘

┌─ SCHEMA OPERATIONS ────────────────────────────────────────────────────────┐
│ CREATE SCHEMA schema_name;          Create new schema                      │
│ DROP SCHEMA schema_name CASCADE;    Delete schema and its objects          │
│ \dn                                 List all schemas                       │
│ SET search_path TO schema_name;     Set current schema                     │
│ SHOW search_path;                   Show current search path               │
└────────────────────────────────────────────────────────────────────────────┘

┌─ TABLE OPERATIONS ─────────────────────────────────────────────────────────┐
│ CREATE TABLE name (                 Create new table                       │
│   id SERIAL PRIMARY KEY,                                                   │
│   name VARCHAR(100)                                                        │
│ );                                                                         │
│                                                                            │
│ DROP TABLE table_name;              Delete table                           │
│ DROP TABLE IF EXISTS table_name;    Delete table if exists                 │
│ TRUNCATE TABLE table_name;          Delete all rows                        │
│ \dt                                 List all tables                        │
│ \d table_name                       Describe table structure               │
│ \d+ table_name                      Describe table with details            │
└────────────────────────────────────────────────────────────────────────────┘

┌─ SELECT QUERIES ───────────────────────────────────────────────────────────┐
│ SELECT * FROM table_name;           Select all columns                     │
│ SELECT col1, col2 FROM table;       Select specific columns                │
│ SELECT * FROM table WHERE id = 1;   Select with condition                  │
│ SELECT * FROM table ORDER BY col;   Select with sorting                    │
│ SELECT * FROM table LIMIT 10;       Select with limit                      │
│ SELECT * FROM table OFFSET 5;       Select with offset                     │
│ SELECT COUNT(*) FROM table;         Count rows                             │
│ SELECT DISTINCT col FROM table;     Select unique values                   │
└────────────────────────────────────────────────────────────────────────────┘

┌─ INSERT, UPDATE, DELETE ───────────────────────────────────────────────────┐
│ INSERT INTO table (col1, col2)      Insert new row                         │
│   VALUES ('val1', 'val2');                                                 │
│                                                                            │
│ INSERT INTO table (col1, col2)      Insert multiple rows                   │
│   VALUES ('a', 'b'), ('c', 'd');                                           │
│                                                                            │
│ UPDATE table SET col1 = 'new'       Update rows                            │
│   WHERE id = 1;                                                            │
│                                                                            │
│ DELETE FROM table WHERE id = 1;     Delete rows                            │
│                                                                            │
│ INSERT ... RETURNING *;             Insert and return inserted row         │
│ UPDATE ... RETURNING *;             Update and return updated rows         │
└────────────────────────────────────────────────────────────────────────────┘

┌─ JOINS ────────────────────────────────────────────────────────────────────┐
│ SELECT * FROM t1                    Inner join                             │
│   INNER JOIN t2 ON t1.id = t2.id;                                          │
│                                                                            │
│ SELECT * FROM t1                    Left join                              │
│   LEFT JOIN t2 ON t1.id = t2.id;                                           │
│                                                                            │
│ SELECT * FROM t1                    Right join                             │
│   RIGHT JOIN t2 ON t1.id = t2.id;                                          │
│                                                                            │
│ SELECT * FROM t1                    Full outer join                        │
│   FULL OUTER JOIN t2 ON t1.id = t2.id;                                     │
└────────────────────────────────────────────────────────────────────────────┘

┌─ INDEXES ──────────────────────────────────────────────────────────────────┐
│ CREATE INDEX idx_name               Create index                           │
│   ON table_name (column_name);                                             │
│                                                                            │
│ CREATE UNIQUE INDEX idx_name        Create unique index                    │
│   ON table_name (column_name);                                             │
│                                                                            │
│ DROP INDEX idx_name;                Delete index                           │
│ \di                                 List all indexes                       │
└────────────────────────────────────────────────────────────────────────────┘

┌─ CONSTRAINTS ──────────────────────────────────────────────────────────────┐
│ ALTER TABLE table_name              Add primary key                        │
│   ADD PRIMARY KEY (id);                                                    │
│                                                                            │
│ ALTER TABLE table_name              Add foreign key                        │
│   ADD FOREIGN KEY (user_id)                                                │
│   REFERENCES users(id);                                                    │
│                                                                            │
│ ALTER TABLE table_name              Add unique constraint                  │
│   ADD UNIQUE (email);                                                      │
│                                                                            │
│ ALTER TABLE table_name              Add check constraint                   │
│   ADD CHECK (age >= 18);                                                   │
└────────────────────────────────────────────────────────────────────────────┘

┌─ USERS & PERMISSIONS ──────────────────────────────────────────────────────┐
│ CREATE USER username                Create new user                        │
│   WITH PASSWORD 'password';                                                │
│                                                                            │
│ DROP USER username;                 Delete user                            │
│ ALTER USER username                 Change password                        │
│   WITH PASSWORD 'newpass';                                                 │
│                                                                            │
│ GRANT ALL ON database               Grant all privileges                   │
│   TO username;                                                             │
│                                                                            │
│ GRANT SELECT ON table_name          Grant specific privilege               │
│   TO username;                                                             │
│                                                                            │
│ REVOKE ALL ON database              Revoke privileges                      │
│   FROM username;                                                           │
│                                                                            │
│ \du                                 List all users/roles                   │
└────────────────────────────────────────────────────────────────────────────┘

┌─ TRANSACTIONS ─────────────────────────────────────────────────────────────┐
│ BEGIN;                              Start transaction                      │
│ COMMIT;                             Commit transaction                     │
│ ROLLBACK;                           Rollback transaction                   │
│                                                                            │
│ Example:                                                                   │
│   BEGIN;                                                                   │
│   UPDATE accounts SET balance = balance - 100 WHERE id = 1;                │
│   UPDATE accounts SET balance = balance + 100 WHERE id = 2;                │
│   COMMIT;                                                                  │
└────────────────────────────────────────────────────────────────────────────┘

┌─ VIEWS ────────────────────────────────────────────────────────────────────┐
│ CREATE VIEW view_name AS            Create view                            │
│   SELECT col1, col2 FROM table;                                            │
│                                                                            │
│ DROP VIEW view_name;                Delete view                            │
│ \dv                                 List all views                         │
└────────────────────────────────────────────────────────────────────────────┘

┌─ FUNCTIONS & PROCEDURES ───────────────────────────────────────────────────┐
│ CREATE FUNCTION func_name()         Create function                        │
│   RETURNS INTEGER AS $$                                                    │
│   BEGIN                                                                    │
│     RETURN 42;                                                             │
│   END;                                                                     │
│   $$ LANGUAGE plpgsql;                                                     │
│                                                                            │
│ DROP FUNCTION func_name;            Delete function                        │
│ \df                                 List all functions                     │
└────────────────────────────────────────────────────────────────────────────┘

┌─ SEQUENCES ────────────────────────────────────────────────────────────────┐
│ CREATE SEQUENCE seq_name;           Create sequence                        │
│ DROP SEQUENCE seq_name;             Delete sequence                        │
│ SELECT nextval('seq_name');         Get next value                         │
│ SELECT currval('seq_name');         Get current value                      │
│ SELECT setval('seq_name', 100);     Set sequence value                     │
│ \ds                                 List all sequences                     │
└────────────────────────────────────────────────────────────────────────────┘

┌─ AGGREGATIONS ─────────────────────────────────────────────────────────────┐
│ SELECT COUNT(*) FROM table;         Count rows                             │
│ SELECT SUM(column) FROM table;      Sum values                             │
│ SELECT AVG(column) FROM table;      Average value                          │
│ SELECT MIN(column) FROM table;      Minimum value                          │
│ SELECT MAX(column) FROM table;      Maximum value                          │
│ SELECT col, COUNT(*)                Group by                               │
│   FROM table GROUP BY col;                                                 │
│ SELECT col, COUNT(*)                Group by with having                   │
│   FROM table GROUP BY col                                                  │
│   HAVING COUNT(*) > 5;                                                     │
└────────────────────────────────────────────────────────────────────────────┘

┌─ STRING FUNCTIONS ─────────────────────────────────────────────────────────┐
│ SELECT CONCAT(str1, str2);          Concatenate strings                    │
│ SELECT UPPER(column) FROM table;    Convert to uppercase                   │
│ SELECT LOWER(column) FROM table;    Convert to lowercase                   │
│ SELECT LENGTH(column) FROM table;   Get string length                      │
│ SELECT SUBSTRING(col, 1, 5);        Extract substring                      │
│ SELECT TRIM(column) FROM table;     Remove whitespace                      │
└────────────────────────────────────────────────────────────────────────────┘

┌─ DATE & TIME ──────────────────────────────────────────────────────────────┐
│ SELECT NOW();                       Current date and time                  │
│ SELECT CURRENT_DATE;                Current date                           │
│ SELECT CURRENT_TIME;                Current time                           │
│ SELECT EXTRACT(YEAR FROM date_col); Extract part of date                   │
│ SELECT date_col + INTERVAL '1 day'; Add interval to date                   │
│ SELECT AGE(date1, date2);           Calculate age/difference               │
└────────────────────────────────────────────────────────────────────────────┘

┌─ JSON OPERATIONS ──────────────────────────────────────────────────────────┐
│ SELECT data->>'key' FROM table;     Extract JSON field as text             │
│ SELECT data->'key' FROM table;      Extract JSON field as JSON             │
│ SELECT data#>>'{a,b}' FROM table;   Extract nested JSON field              │
│ SELECT jsonb_array_elements(data);  Expand JSON array                      │
│ WHERE data @> '{"key":"value"}';    JSON contains                          │
└────────────────────────────────────────────────────────────────────────────┘

┌─ PERFORMANCE & MONITORING ─────────────────────────────────────────────────┐
│ EXPLAIN SELECT * FROM table;        Show query plan                        │
│ EXPLAIN ANALYZE SELECT ...;         Show actual execution stats            │
│ \timing                             Toggle timing display                  │
│ VACUUM table_name;                  Reclaim storage                        │
│ ANALYZE table_name;                 Update statistics                      │
│ SELECT * FROM pg_stat_activity;     Show active queries                    │
└────────────────────────────────────────────────────────────────────────────┘

┌─ BACKUP & RESTORE ─────────────────────────────────────────────────────────┐
│ pg_dump dbname > backup.sql         Backup database (shell command)        │
│ pg_dump -t table dbname > file.sql  Backup single table                    │
│ psql dbname < backup.sql            Restore database (shell command)       │
│ pg_dumpall > all_dbs.sql            Backup all databases                   │
└────────────────────────────────────────────────────────────────────────────┘

EOF
}

# Check for --help flag
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    show_help
    exit 0
fi

# Connect to PostgreSQL
if [ -z "$POSTGRES_URL" ]; then
    echo "Error: POSTGRES_URL environment variable is not set"
    echo ""
    echo "Usage:"
    echo ""
    echo "  In your project root directory,"
    echo ""
    echo "  $ source .env.local.sh"
    echo "  $ ./scripts/postgres.sh"
    echo ""
    echo "Or set manually:"
    echo ""
    echo "  $ export POSTGRES_URL='postgresql://user:pass@localhost:5432/dbname'"
    echo "  $ ./scripts/postgres.sh"
    echo ""
    echo "Or connect directly:"
    echo ""
    echo "  $ psql -h localhost -p 5432 -U username -d database"
    exit 1
fi

psql "$POSTGRES_URL" 2>/dev/null || {
    echo "Error: Failed to connect to PostgreSQL using: psql $POSTGRES_URL"
    echo ""
    echo "Possible solutions:"
    echo "  1. Check if POSTGRES_URL is correct: $POSTGRES_URL"
    echo "  2. Verify PostgreSQL server is running"
    echo "  3. Try connecting directly: psql -h localhost -p 5432 -U username -d database"
    echo "  4. Run './postgres.sh --help' for more information"
    exit 1
}

