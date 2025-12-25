# Madan Sara Database Strategy
## Microservices Database Architecture

**Date**: December 2024  
**Status**: Approved  
**Decision**: Use Existing En Garde PostgreSQL Database with Schema Isolation

---

## Executive Summary

For the En Garde microservices architecture (Langflow, EasyAppointments/EGM Scheduler, MadanSara, Onside, Sankore), we will use the **existing En Garde PostgreSQL database on Railway with schema-based isolation** rather than creating separate databases.

This balances:
- **Operational simplicity** (single database to manage)
- **Cost efficiency** (one Railway PostgreSQL instance)
- **Data integrity** (cross-service queries when needed)
- **Logical separation** (each service has its own schema)

---

## Architecture Decision

### Recommended: Shared Database with Schema Isolation

```
┌─────────────────────────────────────────────────┐
│         PostgreSQL Database (Railway)           │
├─────────────────────────────────────────────────┤
│                                                 │
│  Schema: production_backend                    │
│  ├─ users, brands, campaigns                   │
│  ├─ agents, integrations                       │
│  └─ analytics, insights                        │
│                                                 │
│  Schema: madansara                             │
│  ├─ outreach_campaigns                         │
│  ├─ conversion_events                          │
│  ├─ ab_tests                                   │
│  └─ user_responses                             │
│                                                 │
│  Schema: sankore                               │
│  ├─ ad_trends                                  │
│  ├─ benchmarks                                 │
│  └─ winning_patterns                           │
│                                                 │
│  Schema: onside                                │
│  ├─ content_items                              │
│  ├─ content_analysis                           │
│  └─ content_performance                        │
│                                                 │
│  Schema: langflow                              │
│  ├─ flows, flow_versions                       │
│  ├─ flow_executions                            │
│  └─ flow_logs                                  │
│                                                 │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│           MySQL Database (Railway)              │
├─────────────────────────────────────────────────┤
│                                                 │
│  EasyAppointments/Scheduler                    │
│  ├─ appointments                               │
│  ├─ availability                               │
│  └─ notifications                              │
│                                                 │
│  Note: Separate MySQL database to avoid        │
│  cross-database replication complexity         │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Connection String Pattern

Each microservice connects to the same database but uses a different schema:

```python
# MadanSara
DATABASE_URL = "postgresql://user:pass@host:5432/engarde_db?options=-c%20search_path=madansara,public"

# Sankore
DATABASE_URL = "postgresql://user:pass@host:5432/engarde_db?options=-c%20search_path=sankore,public"

# Onside
DATABASE_URL = "postgresql://user:pass@host:5432/engarde_db?options=-c%20search_path=onside,public"
```

---

## Why NOT Separate Databases?

### ❌ Separate Databases Per Service

**Cons**:
1. **Cost**: Each PostgreSQL instance on Railway costs $5-10/month
2. **Complexity**: Managing 5+ separate databases
3. **Cross-service queries**: Impossible without complex ETL
4. **Backup/restore**: 5x more complex
5. **Connection pooling**: Each database needs its own pool
6. **Railway limits**: Free tier has database limits

**When to use**:
- Massive scale (millions of requests/day per service)
- Different database technologies (e.g., PostgreSQL + MongoDB)
- Strict compliance requirements (data must be physically isolated)

---

## Why YES to Shared Database with Schemas?

### ✅ Shared Database with Schema Isolation

**Pros**:
1. **Cost-effective**: Single PostgreSQL instance ($10/month on Railway)
2. **Simpler operations**: One backup, one restore, one migration
3. **Cross-service analytics**: Can join across schemas when needed
4. **Connection pooling**: Shared pool is more efficient
5. **Development**: Easier local setup (one database)
6. **Logical separation**: Each service owns its schema
7. **Migration path**: Easy to split later if needed

**Cons**:
1. **Noisy neighbor**: One service's heavy queries can affect others
   - **Mitigation**: Connection pool limits per service
2. **Schema conflicts**: Must coordinate schema names
   - **Mitigation**: Clear naming convention
3. **Security**: All services can technically access all schemas
   - **Mitigation**: Use separate database users with schema-specific permissions

---

## Implementation Plan

### 1. Database Setup

```sql
-- Create schemas
CREATE SCHEMA IF NOT EXISTS madansara;
CREATE SCHEMA IF NOT EXISTS sankore;
CREATE SCHEMA IF NOT EXISTS onside;
CREATE SCHEMA IF NOT EXISTS langflow;
CREATE SCHEMA IF NOT EXISTS scheduler;

-- Create service-specific users (optional, for enhanced security)
CREATE USER madansara_user WITH PASSWORD 'secure_password';
GRANT USAGE ON SCHEMA madansara TO madansara_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA madansara TO madansara_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA madansara TO madansara_user;

-- Repeat for other services...
```

### 2. Alembic Configuration (MadanSara Example)

```python
# alembic/env.py
from sqlalchemy import engine_from_config, pool

# Set schema for all operations
target_metadata = Base.metadata
target_metadata.schema = "madansara"

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"options": "-c search_path=madansara,public"}
    )
    
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="madansara",  # Store alembic_version in schema
            include_schemas=True
        )
        
        with context.begin_transaction():
            context.run_migrations()
```

### 3. SQLAlchemy Models

```python
# app/db/base.py
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Base.metadata.schema = "madansara"  # Set schema for all models
```

### 4. Railway Environment Variables

```bash
# MadanSara Service
DATABASE_URL=postgresql://user:pass@postgres.railway.internal:5432/engarde?options=-c%20search_path=madansara,public

# Sankore Service
DATABASE_URL=postgresql://user:pass@postgres.railway.internal:5432/engarde?options=-c%20search_path=sankore,public

# Production Backend (main app)
DATABASE_URL=postgresql://user:pass@postgres.railway.internal:5432/engarde?options=-c%20search_path=production_backend,public
```

---

## Cross-Service Data Access

### When You Need It

**Scenario**: MadanSara needs to know which users belong to which brands (from production_backend schema)

**Solution 1: API Calls** (Recommended)
```python
# MadanSara calls production-backend API
async def get_brand_users(brand_id: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{PRODUCTION_BACKEND_URL}/api/brands/{brand_id}/users"
        )
        return response.json()
```

**Solution 2: Cross-Schema Query** (Use sparingly)
```python
# Direct database query across schemas
from sqlalchemy import text

async def get_brand_users_direct(brand_id: str):
    query = text("""
        SELECT u.id, u.email, u.name
        FROM production_backend.users u
        JOIN production_backend.brand_users bu ON u.id = bu.user_id
        WHERE bu.brand_id = :brand_id
    """)
    
    result = await db.execute(query, {"brand_id": brand_id})
    return result.fetchall()
```

**Best Practice**: Prefer API calls for loose coupling. Use cross-schema queries only for:
- Analytics/reporting
- Background jobs
- Performance-critical paths

---

## Service Mesh Consideration

### Current State: No Service Mesh

For now, services communicate via:
1. **HTTP APIs** (primary)
2. **Shared database** (when absolutely necessary)
3. **Message queue** (future: Redis Pub/Sub or RabbitMQ)

### Future: Service Mesh (Istio/Linkerd)

**When to add**:
- 10+ microservices
- Complex routing requirements
- Need for circuit breakers, retries, timeouts
- Observability requirements (distributed tracing)

**Not needed now** because:
- Only 5-6 services
- Simple communication patterns
- Railway handles load balancing
- Can add later without major refactoring

---

## Migration Path

### If You Need to Split Later

**Scenario**: MadanSara grows to millions of records, needs dedicated database

**Steps**:
1. Create new PostgreSQL instance on Railway
2. Export `madansara` schema: `pg_dump -n madansara > madansara.sql`
3. Import to new database: `psql new_db < madansara.sql`
4. Update `DATABASE_URL` in MadanSara service
5. Drop `madansara` schema from shared database

**Zero downtime**: Use read replicas and gradual cutover

---

## Security Best Practices

### 1. Separate Database Users (Recommended)

```sql
-- Create user per service
CREATE USER madansara_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE engarde TO madansara_user;
GRANT USAGE ON SCHEMA madansara TO madansara_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA madansara TO madansara_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA madansara TO madansara_user;

-- Prevent access to other schemas
REVOKE ALL ON SCHEMA production_backend FROM madansara_user;
REVOKE ALL ON SCHEMA sankore FROM madansara_user;
```

### 2. Connection Pool Limits

```python
# app/db/session.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,          # Max 5 connections per service
    max_overflow=10,      # Allow 10 extra during spikes
    pool_pre_ping=True,   # Verify connections before use
    pool_recycle=3600     # Recycle connections every hour
)
```

### 3. Read-Only Users for Analytics

```sql
CREATE USER analytics_readonly WITH PASSWORD 'readonly_pass';
GRANT CONNECT ON DATABASE engarde TO analytics_readonly;
GRANT USAGE ON SCHEMA madansara, sankore, onside TO analytics_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA madansara, sankore, onside TO analytics_readonly;
```

---

## Monitoring & Observability

### 1. Query Performance

```sql
-- Enable pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Find slow queries by schema
SELECT 
    schemaname,
    query,
    calls,
    total_exec_time,
    mean_exec_time
FROM pg_stat_statements pss
JOIN pg_namespace pn ON pss.query LIKE '%' || pn.nspname || '%'
WHERE pn.nspname IN ('madansara', 'sankore', 'onside')
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### 2. Connection Monitoring

```sql
-- Active connections by schema
SELECT 
    datname,
    usename,
    application_name,
    state,
    COUNT(*)
FROM pg_stat_activity
WHERE datname = 'engarde'
GROUP BY datname, usename, application_name, state;
```

### 3. Schema Size Monitoring

```sql
-- Size of each schema
SELECT 
    schemaname,
    pg_size_pretty(SUM(pg_total_relation_size(schemaname||'.'||tablename))::bigint) as size
FROM pg_tables
WHERE schemaname IN ('madansara', 'sankore', 'onside', 'production_backend')
GROUP BY schemaname
ORDER BY SUM(pg_total_relation_size(schemaname||'.'||tablename)) DESC;
```

---

## Decision Summary

| Aspect | Separate DBs | Shared DB + Schemas | **Decision** |
|--------|-------------|---------------------|--------------|
| **Cost** | High ($50+/mo) | Low ($10/mo) | ✅ Shared |
| **Ops Complexity** | High | Low | ✅ Shared |
| **Data Isolation** | Perfect | Good | ✅ Shared (good enough) |
| **Cross-service queries** | Impossible | Easy | ✅ Shared |
| **Scalability** | Excellent | Good | ✅ Shared (can split later) |
| **Security** | Excellent | Good (with proper users) | ✅ Shared |

**Recommendation**: Use **shared PostgreSQL database with schema isolation** for all En Garde microservices.

---

## Next Steps

1. ✅ Create schemas in Railway PostgreSQL
2. ✅ Update MadanSara to use `madansara` schema
3. ✅ Update Sankore to use `sankore` schema
4. ⏳ Update Onside to use `onside` schema
5. ⏳ Configure Langflow to use `langflow` schema
6. ⏳ Configure EasyAppointments to use `scheduler` schema
7. ⏳ Create service-specific database users (optional, for enhanced security)
