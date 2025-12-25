"""Pytest configuration and shared fixtures."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def tenant_uuid():
    """Generate tenant UUID for testing."""
    return uuid4()


@pytest.fixture
def mock_campaign():
    """Mock outreach campaign."""
    from app.models.outreach import OutreachCampaign

    campaign = Mock(spec=OutreachCampaign)
    campaign.id = uuid4()
    campaign.name = "Test Campaign"
    campaign.channels = ["email", "instagram"]
    campaign.channel_priority = ["email", "instagram"]
    campaign.total_budget = 1000.0
    campaign.budget_per_channel = {"email": 500.0, "instagram": 500.0}
    campaign.messages_per_day = 3
    campaign.messages_per_week = 10
    campaign.start_date = datetime.utcnow()
    campaign.end_date = None
    campaign.status = "active"
    return campaign


@pytest.fixture
def mock_customer_response():
    """Mock customer response message."""
    from app.models.responses import (
        CustomerResponse,
        ResponseStatus,
        ResponseIntent,
        ResponseUrgency,
    )

    response = Mock(spec=CustomerResponse)
    response.id = uuid4()
    response.tenant_uuid = uuid4()
    response.customer_id = "customer_123"
    response.customer_name = "Test Customer"
    response.customer_email = "test@example.com"
    response.channel = "email"
    response.subject = "Test Subject"
    response.message_body = "Test message body"
    response.intent = ResponseIntent.QUESTION
    response.sentiment_score = 0.5
    response.urgency = ResponseUrgency.MEDIUM
    response.status = ResponseStatus.NEW
    response.assigned_to = None
    response.is_flagged = False
    response.is_sla_breached = False
    response.received_at = datetime.utcnow()
    response.first_viewed_at = None
    response.extra_data = {}
    return response


@pytest.fixture
def sample_recipient_profile():
    """Sample recipient profile for testing."""
    return {
        "customer_type": "returning",
        "device": "mobile",
        "timezone": "America/New_York",
        "engagement_history": {
            "email": {"open_rate": 0.3, "click_rate": 0.1, "last_opened": "2024-01-01"},
            "instagram": {"engagement_rate": 0.6, "last_engaged": "2024-01-15"},
        },
        "preferences": {
            "preferred_channel": "email",
            "opt_out_channels": [],
        },
    }


@pytest.fixture
def sample_email_data():
    """Sample email data for testing."""
    return {
        "to": "customer@example.com",
        "subject": "Test Email",
        "body_html": "<p>Test email content</p>",
        "body_text": "Test email content",
        "from_name": "Test Sender",
    }


@pytest.fixture
def sample_classification():
    """Sample AI classification result for testing."""
    return {
        "intent": "purchase_intent",
        "intent_confidence": 0.85,
        "sentiment": {
            "score": 0.7,
            "label": "positive",
        },
        "urgency": {
            "level": "high",
            "reason": "Customer shows strong purchase intent",
        },
        "topics": ["pricing", "product_features"],
        "entities": {
            "products": ["Product A"],
            "issues": [],
            "requests": ["price quote"],
        },
        "next_best_action": {
            "action": "send_pricing_quote",
            "priority": "high",
            "reasoning": "Customer is ready to buy",
        },
        "requires_human": {
            "flag": False,
            "reason": None,
        },
        "suggested_response": {
            "tone": "professional",
            "key_points": ["Provide pricing", "Highlight value", "Include CTA"],
            "template_suggestion": "purchase_inquiry",
        },
    }


# Async test marker
pytest_plugins = ["pytest_asyncio"]
