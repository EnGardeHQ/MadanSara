# Database Schema Setup Status

**Date**: December 24, 2024
**Database**: Railway PostgreSQL
**Connection**: switchback.proxy.rlwy.net:54319/railway

---

## ✅ COMPLETED: Schema Infrastructure

### Schemas Created
All microservice schemas have been successfully created:

| Schema | Status | Tables | Purpose |
|--------|--------|--------|---------|
| `langflow` | ✅ Active | 1 | AI Workflows (already in use) |
| `madansara` | ✅ Created | 0 | Outreach & Conversion (ready for migration) |
| `sankore` | ✅ Created | 0 | Ad Trends & Benchmarks (ready for migration) |
| `onside` | ✅ Created | 0 | Content Management (ready for migration) |
| `production_backend` | ✅ Created | 0 | Core App (optional - can stay in public) |
| `public` | ✅ In Use | 143 | **Current production data** |

### Key Findings

1. **Langflow is already using its schema** ✅
   - Has `alembic_version_langflow` table
   - Properly configured

2. **All other data is in public schema**
   - 143 tables currently in `public` schema
   - Includes: users, brands, campaigns, agents, integrations, etc.

3. **New schemas are empty and ready**
   - `madansara`, `sankore`, `onside` schemas created
   - Permissions configured
   - Ready for Alembic migrations

4. **Scheduler schema may not be needed** (per user feedback)
   - Schema exists but can be dropped if unnecessary
   - EasyAppointments uses MySQL separately

---

## 📋 SQL Operations Completed

All SQL commands from DATABASE_STRATEGY.md have been executed:

```sql
-- ✅ Created Schemas
CREATE SCHEMA IF NOT EXISTS madansara;
CREATE SCHEMA IF NOT EXISTS sankore;
CREATE SCHEMA IF NOT EXISTS onside;
CREATE SCHEMA IF NOT EXISTS langflow;
CREATE SCHEMA IF NOT EXISTS scheduler;
CREATE SCHEMA IF NOT EXISTS production_backend;

-- ✅ Enabled Extensions
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ✅ Granted Permissions
GRANT ALL PRIVILEGES ON SCHEMA madansara TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA sankore TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA onside TO postgres;
GRANT ALL PRIVILEGES ON SCHEMA langflow TO postgres;

-- ✅ Set Default Privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA madansara GRANT ALL PRIVILEGES ON TABLES TO postgres;
-- (and similar for all other schemas)
```

---

## 🚧 NEXT STEPS: Configure Each Microservice

### For MadanSara

#### 1. Update Database Connection String

Add to Railway environment variables or `.env`:

```bash
DATABASE_URL=postgresql://postgres:BTqoCVBmuTAIbtXCNauteEnyeAFHMzpo@switchback.proxy.rlwy.net:54319/railway?options=-c%20search_path=madansara,public
```

#### 2. Update `app/db/base.py`

```python
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
Base.metadata.schema = "madansara"  # All models will use madansara schema
```

#### 3. Update `alembic/env.py`

```python
# Set schema in target metadata
target_metadata.schema = "madansara"

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)

    # Ensure search_path includes madansara schema
    if "options=" not in configuration.get("sqlalchemy.url", ""):
        configuration["sqlalchemy.url"] = configuration["sqlalchemy.url"] + "?options=-c%20search_path=madansara,public"

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="madansara",  # Put alembic_version in madansara schema
            include_schemas=True
        )

        with context.begin_transaction():
            context.run_migrations()
```

#### 4. Run Migrations

```bash
cd /Users/cope/EnGardeHQ/MadanSara
alembic upgrade head
```

This will create tables in the `madansara` schema instead of `public`.

---

### For Sankore

Same process as MadanSara, but use:
```bash
DATABASE_URL=postgresql://postgres:BTqoCVBmuTAIbtXCNauteEnyeAFHMzpo@switchback.proxy.rlwy.net:54319/railway?options=-c%20search_path=sankore,public
```

And set `Base.metadata.schema = "sankore"` in models.

---

### For Onside

Same process, use:
```bash
DATABASE_URL=postgresql://postgres:BTqoCVBmuTAIbtXCNauteEnyeAFHMzpo@switchback.proxy.rlwy.net:54319/railway?options=-c%20search_path=onside,public
```

And set `Base.metadata.schema = "onside"` in models.

---

### For Production Backend (Optional)

**Option 1: Keep using public schema** (current state)
- No changes needed
- All 143 tables remain in `public`
- Works fine for monolithic core app

**Option 2: Migrate to production_backend schema**
- Update connection string to use `production_backend` schema
- Would require migrating existing data
- Not recommended unless needed for isolation

---

## 🔧 Utility Scripts Created

### 1. `setup_schemas.sql`
- Creates all schemas
- Enables extensions
- Sets up permissions
- **Status**: Already executed ✅

### 2. `verify_schemas.sql`
- Lists all schemas
- Shows table counts
- Displays schema sizes
- Shows active connections
- **Usage**: `psql "$DATABASE_PUBLIC_URL" -f verify_schemas.sql`

### 3. Quick Verification Command

```bash
DATABASE_PUBLIC_URL="postgresql://postgres:BTqoCVBmuTAIbtXCNauteEnyeAFHMzpo@switchback.proxy.rlwy.net:54319/railway"

# List all schemas
psql "$DATABASE_PUBLIC_URL" -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_toast', 'pg_catalog', 'information_schema') ORDER BY schema_name;"

# Show table counts per schema
psql "$DATABASE_PUBLIC_URL" -c "SELECT schemaname, COUNT(*) as tables FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema') GROUP BY schemaname ORDER BY schemaname;"
```

---

## 🎯 Current Database Architecture

```
Railway PostgreSQL Database
│
├── public schema (143 tables) ← Current production data
│   ├── users, brands, campaigns, agents
│   ├── integrations, analytics, workflows
│   └── All EasyAppointments (ea_*) tables
│
├── langflow schema (1 table) ← Already configured ✅
│   └── alembic_version_langflow
│
├── madansara schema (0 tables) ← Ready for use
│   └── (waiting for Alembic migration)
│
├── sankore schema (0 tables) ← Ready for use
│   └── (waiting for Alembic migration)
│
├── onside schema (0 tables) ← Ready for use
│   └── (waiting for Alembic migration)
│
├── production_backend schema (0 tables) ← Optional
│   └── (can migrate from public if needed)
│
└── scheduler schema (0 tables) ← May not be needed
    └── (EasyAppointments uses separate MySQL)
```

---

## ⚠️ Important Notes

### No Duplicate Tables

All schemas are currently empty (except langflow). When you run Alembic migrations for each service, new tables will be created in the appropriate schema. There's no risk of duplicates because:

1. Each schema is isolated
2. Tables are created fresh via migrations
3. No data migration from `public` schema (unless you explicitly do it)

### Langflow Status

Langflow is already properly configured and using the `langflow` schema. No action needed.

### Scheduler Note

Per your feedback, the scheduler schema may not be needed:
- EasyAppointments uses a separate MySQL database
- The `scheduler` schema can be dropped if unnecessary
- Command to drop: `DROP SCHEMA IF EXISTS scheduler CASCADE;`

---

## 📊 Verification Results

### Current Connection Test

```
Active Connections:
- postgres user: engarde_backend (idle)
- postgres user: psql (active)

Schemas Created: 7
Tables in public: 143
Tables in langflow: 1
Tables in madansara: 0 (ready)
Tables in sankore: 0 (ready)
Tables in onside: 0 (ready)
```

---

## ✅ Success Criteria Met

- [x] All microservice schemas created
- [x] Database extensions enabled (pg_stat_statements, uuid-ossp)
- [x] Permissions configured for postgres user
- [x] Default privileges set for future tables
- [x] Verification scripts created
- [x] Documentation complete
- [x] No duplicate tables (schemas are empty)
- [x] Langflow already properly configured

---

## 🚀 Ready to Deploy

Each microservice can now:
1. Update its DATABASE_URL to use its schema
2. Configure SQLAlchemy models with the schema
3. Run Alembic migrations to create tables
4. Start using the isolated schema

**No risk of data loss or duplication** - all new tables will be created fresh in their respective schemas.

---

**Files Created**:
- `setup_schemas.sql` - Schema creation script (executed)
- `verify_schemas.sql` - Verification queries
- `SCHEMA_SETUP_COMPLETE.md` - Initial completion report
- `DATABASE_SETUP_STATUS.md` - This status document

**Database Connection**:
```bash
postgresql://postgres:BTqoCVBmuTAIbtXCNauteEnyeAFHMzpo@switchback.proxy.rlwy.net:54319/railway
```
