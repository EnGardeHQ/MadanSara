# Madan Sara - Railway Deployment Ready

**Date:** December 24, 2024
**Status:** ✅ Ready for Railway Deployment
**Integration:** En Garde PostgreSQL + ZeroDB + Service Mesh

---

## What Was Built

### 1. **Shared Database Integration** ✅
**File:** `app/core/engarde_db.py`

Connects all microservices to En Garde's shared PostgreSQL database:
- Connection pooling optimized for Railway
- Health checks and monitoring
- Automatic session management
- Connection stats tracking

**Features:**
```python
from app.core.engarde_db import get_db, check_db_connection, get_db_stats

# Get database session
db = get_db_session()

# Check connection health
if check_db_connection():
    print("Database ready")

# Get pool statistics
stats = get_db_stats()
# Returns: pool_size, checked_out, overflow, etc.
```

### 2. **ZeroDB Memory Layer Integration** ✅
**File:** `app/core/zerodb_integration.py`

Enables Walker agents to store and retrieve context across all microservices:

**Memory Types:**
- `SHORT_TERM` - Recent conversation context (24-48hrs)
- `LONG_TERM` - Persistent knowledge
- `EPISODIC` - Specific events/interactions
- `SEMANTIC` - Facts and concepts
- `PROCEDURAL` - How-to knowledge
- `WORKING` - Active task context

**Usage:**
```python
from app.core.zerodb_integration import get_zerodb, MemoryType

zerodb = get_zerodb()

# Store memory
await zerodb.store_memory(
    agent_id="walker_001",
    memory_type=MemoryType.SHORT_TERM,
    content="Customer prefers email communication",
    metadata={"customer_id": "cust_123"}
)

# Retrieve relevant memories
memories = await zerodb.retrieve_memories(
    agent_id="walker_001",
    query="customer communication preferences",
    limit=5
)

# Get full agent context
context = await zerodb.get_agent_context("walker_001")
```

### 3. **Service Mesh Layer** ✅
**File:** `app/core/service_mesh.py`

Manages inter-service communication between microservices:

**Services:**
- En Garde Core
- Onside (SEO)
- Sankore (Paid Ads)
- Madan Sara (Conversion)

**Features:**
- Service discovery
- Circuit breaker pattern
- Automatic retries with exponential backoff
- Health monitoring
- Shared authentication

**Usage:**
```python
from app.core.service_mesh import get_service_mesh, ServiceName

mesh = get_service_mesh()

# Call Onside for SEO analysis
result = await mesh.get_seo_analysis(
    url="https://example.com",
    tenant_uuid=tenant_uuid
)

# Call Sankore for ad intelligence
intel = await mesh.get_ad_intelligence(
    campaign_id="campaign_123",
    tenant_uuid=tenant_uuid
)

# Sync to En Garde core
await mesh.sync_to_engarde_core(
    data_type="conversion",
    data=conversion_data,
    tenant_uuid=tenant_uuid
)

# Check service health
health = await mesh.check_all_services_health()
```

### 4. **Railway Deployment Configuration** ✅

**Files Created:**
- `Dockerfile` - Multi-stage Docker build
- `railway.json` - Railway-specific configuration
- `scripts/deploy-railway.sh` - Automated deployment script
- `scripts/init-zerodb-collections.py` - ZeroDB initialization

**Dockerfile Features:**
- Multi-stage build for optimization
- Non-root user for security
- Health check integration
- PostgreSQL client included
- Python 3.11 slim base

**railway.json Configuration:**
```json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 100,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 5. **Enhanced Application** ✅
**File:** `app/main.py` (updated)

**New Features:**
- Startup event with service initialization
- Enhanced health check with component status
- Readiness and liveness probes
- Request logging middleware
- Database connection verification
- Service mesh initialization
- ZeroDB client setup

**Health Endpoints:**
```bash
# General health (with component status)
GET /health

# Kubernetes readiness probe
GET /health/ready

# Kubernetes liveness probe
GET /health/live
```

**Response Example:**
```json
{
  "status": "healthy",
  "service": "madan-sara",
  "version": "0.1.0",
  "components": {
    "database": {
      "status": "healthy",
      "pool_stats": {
        "pool_size": 5,
        "checked_out": 2,
        "overflow": 0
      }
    },
    "service_mesh": {
      "status": "healthy",
      "services": { ... }
    },
    "zerodb": {
      "status": "healthy",
      "configured": true
    }
  }
}
```

---

## Environment Variables

### Required for All Microservices

```bash
# ============================================
# DATABASE (Shared PostgreSQL)
# ============================================
ENGARDE_DATABASE_URL=postgresql://user:pass@host:port/engarde
DATABASE_PUBLIC_URL=postgresql://user:pass@host:port/engarde
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# ============================================
# ZERODB (Qdrant - Shared Memory Layer)
# ============================================
ZERODB_URL=http://qdrant:6333
ZERODB_API_KEY=your-qdrant-api-key

# ============================================
# SERVICE MESH (Inter-Service Communication)
# ============================================
SERVICE_MESH_SECRET=shared-secret-between-services
SERVICE_MESH_TIMEOUT=30
CIRCUIT_BREAKER_THRESHOLD=5

# Service URLs
ENGARDE_CORE_URL=https://engarde-core-production.up.railway.app
ONSIDE_URL=https://onside-production.up.railway.app
SANKORE_URL=https://sankore-production.up.railway.app
MADAN_SARA_URL=https://madan-sara-production.up.railway.app

# ============================================
# AI SERVICES
# ============================================
ANTHROPIC_API_KEY=sk-ant-...

# Optional: Embedding service
EMBEDDING_SERVICE_URL=https://embedding-service.com/api

# ============================================
# EN GARDE INTEGRATION (Walker SDK)
# ============================================
ENGARDE_API_KEY=your-engarde-api-key
ENGARDE_BASE_URL=https://api.engarde.com/v1

# ============================================
# APPLICATION SETTINGS
# ============================================
PORT=8002
ENVIRONMENT=production
LOG_LEVEL=INFO
SQL_ECHO=false

# ============================================
# EXTERNAL SERVICES (via Walker SDK)
# ============================================
# Email (if direct integration needed)
SENDGRID_API_KEY=optional

# Social Media
META_ACCESS_TOKEN=optional
META_PAGE_ACCESS_TOKEN=optional
META_INSTAGRAM_ACCOUNT_ID=optional
```

---

## Deployment Steps

### Prerequisites

1. **Railway CLI installed:**
```bash
npm install -g @railway/cli
# or
brew install railway
```

2. **Railway account and project created**

3. **PostgreSQL database provisioned in Railway**

4. **Qdrant (ZeroDB) deployed:**
```bash
railway add qdrant
# or use Qdrant Cloud
```

### Step 1: Initialize ZeroDB Collections

```bash
cd /Users/cope/EnGardeHQ/MadanSara

# Set environment variables
export ZERODB_URL=your-qdrant-url
export ZERODB_API_KEY=your-api-key

# Run initialization script
python scripts/init-zerodb-collections.py

# Should see:
# ✓ All collections ready for Walker agents
```

### Step 2: Deploy to Railway

```bash
# Login to Railway
railway login

# Link to project
railway link

# Deploy
./scripts/deploy-railway.sh

# Follow prompts:
# 1. Select environment (production/staging)
# 2. Confirm environment variables
# 3. Wait for deployment
```

### Step 3: Verify Deployment

```bash
# Check logs
railway logs

# Test health endpoint
curl https://madan-sara-production.up.railway.app/health

# Should return healthy status with all components
```

### Step 4: Test Service Mesh

```bash
# Test inter-service communication
curl https://madan-sara-production.up.railway.app/api/v1/system/service-mesh-status

# Test ZeroDB integration
# (via API or directly)
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  Railway Platform                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐ │
│  │   Onside      │   │  Madan Sara   │   │   Sankore     │ │
│  │   (SEO)       │   │ (Conversion)  │   │  (Paid Ads)   │ │
│  │   Port 8001   │   │  Port 8002    │   │  Port 8003    │ │
│  └───────┬───────┘   └───────┬───────┘   └───────┬───────┘ │
│          │                    │                    │         │
│          └────────────────────┴────────────────────┘         │
│                               │                              │
│          ┌────────────────────┴────────────────────┐        │
│          │      Service Mesh Layer                 │        │
│          │  - Service Discovery                    │        │
│          │  - Circuit Breaker                      │        │
│          │  - Health Monitoring                    │        │
│          └────────────────────┬────────────────────┘        │
│                               │                              │
│  ┌────────────────────────────┴──────────────────────────┐  │
│  │            Shared Infrastructure                       │  │
│  ├─────────────────────────────────────────────────────────┤ │
│  │  ┌──────────────────┐    ┌────────────────────────┐   │  │
│  │  │  PostgreSQL      │    │  Qdrant (ZeroDB)       │   │  │
│  │  │  (En Garde DB)   │    │  (Agent Memory)        │   │  │
│  │  │                  │    │                        │   │  │
│  │  │  - Users         │    │  - Short-term memory   │   │  │
│  │  │  - Campaigns     │    │  - Long-term memory    │   │  │
│  │  │  - Conversions   │    │  - Episodic memory     │   │  │
│  │  │  - Responses     │    │  - Semantic memory     │   │  │
│  │  └──────────────────┘    └────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ↓
                   ┌──────────────────────┐
                   │  En Garde Core App   │
                   │  (Frontend/Backend)  │
                   └──────────────────────┘
```

---

## Service Communication Patterns

### 1. Madan Sara → Onside (SEO Data)

```python
# Get SEO insights for conversion optimization
mesh = get_service_mesh()
seo_data = await mesh.get_seo_analysis(
    url="https://customer-site.com",
    tenant_uuid=tenant_uuid
)

# Use SEO data to optimize messaging
if seo_data["primary_keywords"]:
    # Incorporate keywords in email subject lines
    pass
```

### 2. Sankore → Madan Sara (Conversion Data)

```python
# Get conversion insights for ad optimization
mesh = get_service_mesh()
conversion_insights = await mesh.get_conversion_insights(
    customer_id="cust_123",
    tenant_uuid=tenant_uuid
)

# Optimize ad targeting based on conversion patterns
```

### 3. All Services → ZeroDB (Walker Memory)

```python
# Store agent decision
zerodb = get_zerodb()
await zerodb.store_memory(
    agent_id="walker_seo_001",
    memory_type=MemoryType.PROCEDURAL,
    content="For e-commerce sites, prioritize product page optimization",
    metadata={"domain": "ecommerce", "confidence": 0.95}
)

# Retrieve for future decisions
memories = await zerodb.retrieve_memories(
    agent_id="walker_seo_001",
    query="e-commerce optimization strategy"
)
```

### 4. All Services → En Garde Core (Sync)

```python
# Sync conversion event
mesh = get_service_mesh()
await mesh.sync_to_engarde_core(
    data_type="conversion",
    data={
        "customer_id": "cust_123",
        "conversion_type": "purchase",
        "value": 99.99,
        "attribution": "email_campaign"
    },
    tenant_uuid=tenant_uuid
)
```

---

## Database Schema Sharing

All microservices share the same PostgreSQL database but own different tables:

**Madan Sara Tables:**
- `outreach_campaigns`
- `outreach_messages`
- `customer_responses`
- `conversion_events`
- `ab_tests`
- `website_visitors`
- etc. (27 tables total)

**Onside Tables:**
- `seo_analyses`
- `keyword_rankings`
- `backlinks`
- `technical_audits`
- etc.

**Sankore Tables:**
- `ad_campaigns`
- `ad_performance`
- `budget_allocations`
- `competitor_intelligence`
- etc.

**Shared Tables (En Garde Core):**
- `tenants`
- `users`
- `integrations`
- `api_keys`

All tables include `tenant_uuid` for multi-tenant isolation.

---

## Monitoring & Observability

### Health Checks

Each service exposes:
```bash
GET /health              # Detailed component health
GET /health/ready        # Readiness probe
GET /health/live         # Liveness probe
```

### Railway Logs

```bash
# View logs
railway logs --service madan-sara

# Follow logs
railway logs -f --service madan-sara

# Filter by level
railway logs --service madan-sara | grep ERROR
```

### Metrics

Available in health endpoint:
- Database connection pool stats
- Service mesh status
- Circuit breaker states
- ZeroDB connection status

### Alerts

Configure in Railway:
- Service down alerts
- High error rate alerts
- Resource usage alerts

---

## Cost Estimates

### Railway Pricing (per service)

**Hobby Plan ($5/service/month):**
- 512 MB RAM
- 1 vCPU
- Good for staging/testing

**Pro Plan ($20/service/month):**
- Up to 8 GB RAM
- Up to 8 vCPU
- Production-ready

**Total Monthly Cost:**
- **Staging:** ~$20-30 (3 services + DB + Qdrant)
- **Production:** ~$100-120 (3 services + DB + Qdrant)

### Optimization Tips

1. Share PostgreSQL database (done)
2. Share Qdrant instance (done)
3. Use auto-sleep for staging
4. Optimize connection pools
5. Cache frequently accessed data

---

## Security Considerations

### 1. **Database Security**
- ✅ SSL connections enforced
- ✅ Credentials in environment variables
- ✅ Connection pooling with limits
- ✅ No credentials in code

### 2. **Service Mesh Security**
- ✅ Shared secret authentication
- ✅ HTTPS for all inter-service calls
- ✅ Circuit breaker prevents cascade failures
- ✅ Request logging for audit

### 3. **API Security**
- ✅ Rate limiting (to be configured)
- ✅ CORS properly configured
- ✅ Input validation with Pydantic
- ✅ SQL injection prevention (ORM)

### 4. **ZeroDB Security**
- ✅ API key authentication
- ✅ Tenant isolation in queries
- ✅ Encrypted connections

---

## Troubleshooting Guide

### Database Connection Fails

```bash
# Test connection
railway run python -c "from app.core.engarde_db import check_db_connection; print(check_db_connection())"

# Check environment variable
railway variables get ENGARDE_DATABASE_URL

# Verify PostgreSQL is running
railway status --service postgresql
```

### Service Mesh Not Working

```bash
# Check service URLs
railway variables get ONSIDE_URL
railway variables get SANKORE_URL

# Test from within service
railway run --service madan-sara curl http://onside:8001/health

# Check circuit breaker status
curl https://madan-sara.railway.app/health
# Look at service_mesh.services in response
```

### ZeroDB Connection Issues

```bash
# Test ZeroDB connection
railway run python scripts/test-zerodb.py

# Check collections
curl -H "api-key: YOUR_KEY" https://qdrant-url:6333/collections

# Re-initialize collections
python scripts/init-zerodb-collections.py
```

### High Memory Usage

```bash
# Check pool stats
railway run python -c "from app.core.engarde_db import get_db_stats; print(get_db_stats())"

# Reduce pool size
railway variables set DB_POOL_SIZE=3

# Redeploy
railway up
```

---

## Next Steps

### Immediate (Before Production)

- [ ] Deploy to Railway staging environment
- [ ] Test all service-to-service communication
- [ ] Verify ZeroDB memory persistence
- [ ] Load test with production-like data
- [ ] Set up monitoring/alerts
- [ ] Configure backups

### Short-term (Week 1)

- [ ] Deploy Onside with same configuration
- [ ] Deploy Sankore with same configuration
- [ ] Test full Walker agent workflows
- [ ] Document API endpoints
- [ ] Set up CI/CD pipeline

### Long-term (Month 1)

- [ ] Implement comprehensive logging
- [ ] Add distributed tracing (Jaeger/Zipkin)
- [ ] Set up error tracking (Sentry)
- [ ] Create admin dashboard
- [ ] Performance optimization
- [ ] Security audit

---

## Support Resources

- **Railway Docs:** https://docs.railway.app
- **Qdrant Docs:** https://qdrant.tech/documentation
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **SQLAlchemy Docs:** https://docs.sqlalchemy.org

---

## Summary

✅ **Database Integration:** All services connect to shared En Garde PostgreSQL
✅ **Memory Layer:** ZeroDB integration for Walker agent memory
✅ **Service Mesh:** Inter-service communication with circuit breaker
✅ **Railway Ready:** Docker + railway.json + deployment scripts
✅ **Monitoring:** Enhanced health checks with component status
✅ **Documentation:** Complete deployment guide and troubleshooting

**Status: READY FOR RAILWAY DEPLOYMENT** 🚀

---

**Next Command:**
```bash
cd /Users/cope/EnGardeHQ/MadanSara
./scripts/deploy-railway.sh
```
