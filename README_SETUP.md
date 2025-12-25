# Madan Sara - Setup Guide

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Node.js 18+ (for frontend)

### Installation

1. **Create virtual environment:**
```bash
cd /Users/cope/EnGardeHQ/MadanSara
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Setup environment variables:**
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

4. **Setup database:**
```bash
# Create database
createdb madansara

# Run migrations
alembic upgrade head
```

5. **Run the application:**
```bash
uvicorn app.main:app --reload --port 8002
```

The API will be available at: http://localhost:8002

API documentation: http://localhost:8002/docs

### Development

**Run tests:**
```bash
pytest
```

**Format code:**
```bash
black app/
ruff check app/ --fix
```

**Type checking:**
```bash
mypy app/
```

### Project Structure

```
MadanSara/
├── app/
│   ├── main.py                 # FastAPI application entry
│   ├── models/                 # SQLAlchemy models
│   ├── routers/                # API endpoints
│   ├── services/               # Business logic
│   │   ├── orchestrator/       # Multi-channel orchestration
│   │   ├── channels/           # Channel implementations
│   │   │   ├── email/
│   │   │   ├── instagram/
│   │   │   ├── facebook/
│   │   │   ├── linkedin/
│   │   │   ├── twitter/
│   │   │   ├── whatsapp/
│   │   │   └── chat/
│   │   ├── tracking/           # Website funnel tracking
│   │   ├── ab_testing/         # A/B testing engine
│   │   ├── attribution/        # Conversion attribution
│   │   ├── responses/          # Response management
│   │   └── ai_classification/  # AI-powered classification
│   ├── schemas/                # Pydantic schemas
│   └── core/                   # Core utilities
├── alembic/                    # Database migrations
├── tests/                      # Test suite
├── docs/                       # Documentation
└── frontend/                   # React dashboard
```

### API Endpoints

- `GET /health` - Health check
- `POST /api/v1/outreach/send` - Send multi-channel outreach
- `GET /api/v1/conversion/stats` - Conversion statistics
- `POST /api/v1/ab-tests/create` - Create A/B test
- `GET /api/v1/responses/inbox` - Unified inbox
- `POST /api/v1/website/track` - Track website events

### Environment Variables

See `.env.example` for all required configuration variables.

Key variables:
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `ANTHROPIC_API_KEY` - Claude API key
- `SENDGRID_API_KEY` - Email service
- `TWILIO_AUTH_TOKEN` - SMS/WhatsApp service

### Next Steps

1. Complete database model implementation
2. Setup Alembic migrations
3. Implement Outreach Orchestrator
4. Build channel services (Email first)
5. Deploy to Railway

For detailed implementation plan, see:
- `MASTER_ROADMAP.md` - 24-week implementation plan
- `TODO.md` - Detailed task list (123 tasks)
- `BEST_PRACTICES_STRATEGY.md` - Intelligence strategy
