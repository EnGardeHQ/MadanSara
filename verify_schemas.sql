-- ============================================================================
-- Schema Verification and Monitoring Queries
-- Based on DATABASE_STRATEGY.md monitoring section
-- ============================================================================

\echo '==================================================================='
\echo 'SCHEMA VERIFICATION REPORT'
\echo '==================================================================='
\echo ''

-- 1. List all microservice schemas
\echo '1. SCHEMAS:'
\echo '-------------------------------------------------------------------'
SELECT
    schema_name,
    CASE
        WHEN schema_name = 'madansara' THEN 'MadanSara - Outreach & Conversion'
        WHEN schema_name = 'sankore' THEN 'Sankore - Ad Trends & Benchmarks'
        WHEN schema_name = 'onside' THEN 'Onside - Content Management'
        WHEN schema_name = 'langflow' THEN 'Langflow - AI Workflows'
        WHEN schema_name = 'scheduler' THEN 'EasyAppointments - Scheduling'
        WHEN schema_name = 'production_backend' THEN 'Production Backend - Core App'
        ELSE 'Unknown'
    END as description
FROM information_schema.schemata
WHERE schema_name IN ('madansara', 'sankore', 'onside', 'langflow', 'scheduler', 'production_backend')
ORDER BY schema_name;

\echo ''
\echo '2. SCHEMA SIZES:'
\echo '-------------------------------------------------------------------'
SELECT
    schemaname as schema,
    COUNT(tablename) as table_count,
    pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as total_size
FROM pg_tables
WHERE schemaname IN ('madansara', 'sankore', 'onside', 'production_backend', 'langflow', 'scheduler')
GROUP BY schemaname
ORDER BY SUM(pg_total_relation_size(schemaname||'.'||tablename)) DESC;

\echo ''
\echo '3. TABLES PER SCHEMA:'
\echo '-------------------------------------------------------------------'
SELECT
    schemaname as schema,
    tablename as table,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname IN ('madansara', 'sankore', 'onside', 'production_backend', 'langflow', 'scheduler')
ORDER BY schemaname, tablename;

\echo ''
\echo '4. ACTIVE CONNECTIONS:'
\echo '-------------------------------------------------------------------'
SELECT
    datname as database,
    usename as user,
    application_name,
    state,
    COUNT(*) as connection_count
FROM pg_stat_activity
WHERE datname = current_database()
GROUP BY datname, usename, application_name, state
ORDER BY connection_count DESC;

\echo ''
\echo '5. EXTENSIONS ENABLED:'
\echo '-------------------------------------------------------------------'
SELECT
    extname as extension,
    extversion as version
FROM pg_extension
WHERE extname IN ('pg_stat_statements', 'uuid-ossp', 'pgcrypto')
ORDER BY extname;

\echo ''
\echo '==================================================================='
\echo 'VERIFICATION COMPLETE'
\echo '==================================================================='
