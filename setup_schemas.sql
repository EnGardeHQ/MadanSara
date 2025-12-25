-- ============================================================================
-- En Garde Microservices Database Schema Setup
-- Based on DATABASE_STRATEGY.md
-- Date: December 24, 2024
-- ============================================================================

-- 1. CREATE SCHEMAS
-- ============================================================================

-- Create schema for MadanSara (outreach/conversion service)
CREATE SCHEMA IF NOT EXISTS madansara;

-- Create schema for Sankore (ad trends/benchmarks service)
CREATE SCHEMA IF NOT EXISTS sankore;

-- Create schema for Onside (content management service)
CREATE SCHEMA IF NOT EXISTS onside;

-- Create schema for Langflow (AI workflow service)
CREATE SCHEMA IF NOT EXISTS langflow;

-- Create schema for Scheduler/EasyAppointments
CREATE SCHEMA IF NOT EXISTS scheduler;

-- Create schema for production backend (if not exists)
CREATE SCHEMA IF NOT EXISTS production_backend;


-- 2. ENABLE EXTENSIONS
-- ============================================================================

-- Enable pg_stat_statements for query performance monitoring
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Enable UUID generation (useful for primary keys)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


-- 3. GRANT PERMISSIONS TO POSTGRES USER
-- ============================================================================

-- Grant all privileges to postgres user on all schemas
GRANT ALL PRIVILEGES ON SCHEMA madansara TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA sankore TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA onside TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA langflow TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA scheduler TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA production_backend TO postgres;

-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO postgres;


-- 4. SET DEFAULT PRIVILEGES
-- ============================================================================

-- For madansara schema
ALTER DEFAULT PRIVILEGES IN SCHEMA madansara
GRANT ALL PRIVILEGES ON TABLES TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA madansara
GRANT ALL PRIVILEGES ON SEQUENCES TO postgres;

-- For sankore schema
ALTER DEFAULT PRIVILEGES IN SCHEMA sankore
GRANT ALL PRIVILEGES ON TABLES TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA sankore
GRANT ALL PRIVILEGES ON SEQUENCES TO postgres;

-- For onside schema
ALTER DEFAULT PRIVILEGES IN SCHEMA onside
GRANT ALL PRIVILEGES ON TABLES TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA onside
GRANT ALL PRIVILEGES ON SEQUENCES TO postgres;

-- For langflow schema
ALTER DEFAULT PRIVILEGES IN SCHEMA langflow
GRANT ALL PRIVILEGES ON TABLES TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA langflow
GRANT ALL PRIVILEGES ON SEQUENCES TO postgres;

-- For scheduler schema
ALTER DEFAULT PRIVILEGES IN SCHEMA scheduler
GRANT ALL PRIVILEGES ON TABLES TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA scheduler
GRANT ALL PRIVILEGES ON SEQUENCES TO postgres;

-- For production_backend schema
ALTER DEFAULT PRIVILEGES IN SCHEMA production_backend
GRANT ALL PRIVILEGES ON TABLES TO postgres;

ALTER DEFAULT PRIVILEGES IN SCHEMA production_backend
GRANT ALL PRIVILEGES ON SEQUENCES TO postgres;


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- List all schemas
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('madansara', 'sankore', 'onside', 'langflow', 'scheduler', 'production_backend')
ORDER BY schema_name;

-- Show schema sizes (will be 0 initially)
SELECT
    schemaname,
    pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as size
FROM pg_tables
WHERE schemaname IN ('madansara', 'sankore', 'onside', 'production_backend', 'langflow', 'scheduler')
GROUP BY schemaname
ORDER BY SUM(pg_total_relation_size(schemaname||'.'||tablename)) DESC;

-- ============================================================================
-- SETUP COMPLETE
-- ============================================================================
