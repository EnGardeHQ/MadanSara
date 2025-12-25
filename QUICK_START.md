# Madan Sara - Quick Start Guide

Get up and running with Madan Sara in 5 minutes.

## Prerequisites

- Python 3.11+
- PostgreSQL 14+
- En Garde API access

## Setup

### 1. Clone & Install

```bash
cd /Users/cope/EnGardeHQ/MadanSara

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Minimum required configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/madan_sara
ENGARDE_API_KEY=your_engarde_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
PORT=8002
```

### 3. Database Setup

```bash
# Create database
createdb madan_sara

# Run migrations
alembic upgrade head
```

### 4. Run Tests

```bash
# Verify installation
pytest

# Should see: 100+ tests passing
```

### 5. Start Server

```bash
# Development mode
python app/main.py

# Server starts at http://localhost:8002
```

### 6. Test API

```bash
# Health check
curl http://localhost:8002/health

# View API docs
open http://localhost:8002/docs
```

## Quick Examples

### Send Outreach Message

```bash
curl -X POST http://localhost:8002/api/v1/outreach/send \
  -H "Content-Type: application/json" \
  -d '{
    "campaign_id": "uuid-here",
    "recipient_id": "customer_123",
    "recipient_profile": {
      "customer_type": "new",
      "device": "mobile"
    },
    "content": {
      "email": "Email content here",
      "instagram": "IG content here"
    }
  }'
```

### Classify Customer Message

```bash
curl -X POST http://localhost:8002/api/v1/responses/classify \
  -H "Content-Type: application/json" \
  -d '{
    "response_id": "uuid-here"
  }'
```

### Get Unified Inbox

```bash
curl http://localhost:8002/api/v1/responses/inbox?tenant_uuid=UUID&status=new
```

## Key Integrations

### Walker SDK (En Garde Integration)

The Walker SDK automatically connects to En Garde's integrations:

```python
from app.services.integrations.walker_sdk import WalkerAgentSDK

sdk = WalkerAgentSDK()

# Get tenant's configured integrations
integrations = await sdk.get_tenant_integrations(tenant_uuid)

# Send email through tenant's provider
result = await sdk.send_email_via_integration(
    tenant_uuid=tenant_uuid,
    integration_id="email_sendgrid",
    email_data={
        "to": "customer@example.com",
        "subject": "Hello",
        "body_html": "<p>Content</p>"
    }
)
```

### AI Classification

```python
from app.services.ai_classification.classifier import AIResponseClassifier

classifier = AIResponseClassifier()

# Classify message
classification = await classifier.classify_response(
    message_text="I want to buy this product",
    channel="email"
)

# Returns: intent, sentiment, urgency, next_best_action
```

### Orchestrator

```python
from app.services.orchestrator.orchestrator import OutreachOrchestrator

orchestrator = OutreachOrchestrator(db)

# Send with intelligent routing
result = await orchestrator.send_outreach(
    campaign=campaign,
    recipient_id="customer_123",
    recipient_profile=profile,
    content=content
)

# Automatically handles:
# - Channel selection
# - Deduplication
# - Budget checking
# - Scheduling
```

## Architecture Overview

```
Request → FastAPI Router → Service Layer → Database
                        ↓
                   Walker SDK → En Garde API → Integrations
                        ↓
                   Claude AI → Classification
```

## File Structure

```
app/
├── models/              # SQLAlchemy models (27 tables)
├── services/
│   ├── orchestrator/    # Routing & coordination
│   ├── ai_classification/  # Claude integration
│   ├── integrations/    # Walker SDK
│   ├── channels/        # Email, Instagram, Facebook
│   ├── inbox/           # Unified inbox
│   ├── ab_testing/      # A/B test engine
│   └── tracking/        # Website tracking
├── routers/             # FastAPI routers
└── core/                # Config & database

tests/
├── unit/                # 100+ unit tests
└── conftest.py          # Shared fixtures
```

## Common Tasks

### Run Specific Tests

```bash
# Test orchestrator
pytest tests/unit/test_orchestrator.py -v

# Test AI classifier
pytest tests/unit/test_ai_classifier.py -v

# Test with coverage
pytest --cov=app --cov-report=html
```

### Create New Migration

```bash
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### View API Docs

- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc
- OpenAPI JSON: http://localhost:8002/openapi.json

## Troubleshooting

### Database Connection Error

```bash
# Check PostgreSQL is running
pg_isready

# Verify connection string
echo $DATABASE_URL
```

### Import Errors

```bash
# Ensure you're in project root
cd /Users/cope/EnGardeHQ/MadanSara

# Reinstall dependencies
pip install -r requirements.txt
```

### Test Failures

```bash
# Run tests in verbose mode
pytest -v --tb=long

# Check test configuration
cat pytest.ini
```

## Next Steps

1. **Review Documentation**
   - Read `IMPLEMENTATION_COMPLETE.md` for full details
   - Check `ORCHESTRATOR_GUIDE.md` for orchestrator deep dive

2. **Integration Testing**
   - Test with actual En Garde API
   - Verify Walker SDK connections

3. **Deployment**
   - Configure production environment
   - Deploy to Railway (when ready)

## Support

For issues or questions:
1. Check `IMPLEMENTATION_COMPLETE.md`
2. Review API docs at `/docs`
3. Check test files for usage examples

---

**Built with Claude Code for En Garde HQ**
