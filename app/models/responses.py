"""Response management and unified inbox models."""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Float, ForeignKey, Enum, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ResponseStatus(str, enum.Enum):
    """Status of customer response."""
    NEW = "new"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AI_DRAFT_READY = "ai_draft_ready"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    SENT = "sent"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ResponseIntent(str, enum.Enum):
    """Classified intent of customer response."""
    PURCHASE = "purchase"
    QUESTION = "question"
    OBJECTION = "objection"
    COMPLAINT = "complaint"
    COMPLIMENT = "compliment"
    UNSUBSCRIBE = "unsubscribe"
    SPAM = "spam"
    OTHER = "other"


class ResponseUrgency(str, enum.Enum):
    """Urgency level of response."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CustomerResponse(Base):
    """Unified inbox for all customer responses across channels."""
    __tablename__ = "customer_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Source
    channel = Column(String(50), nullable=False, index=True)
    original_message_id = Column(UUID(as_uuid=True), index=True)  # Outreach message that triggered this
    campaign_id = Column(UUID(as_uuid=True), index=True)
    external_message_id = Column(String(255))  # Platform-specific ID

    # Customer
    customer_id = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255))
    customer_email = Column(String(255), index=True)
    customer_phone = Column(String(50))
    customer_social_handle = Column(String(255))

    # Content
    subject = Column(String(500))  # For email
    message_body = Column(Text, nullable=False)
    message_html = Column(Text)
    attachments = Column(JSON)  # File attachments metadata

    # AI Classification
    intent = Column(Enum(ResponseIntent), index=True)
    intent_confidence = Column(Float)  # 0.0-1.0
    sentiment_score = Column(Float)  # -1.0 to 1.0 (negative to positive)
    urgency = Column(Enum(ResponseUrgency), default=ResponseUrgency.MEDIUM, index=True)
    key_topics = Column(JSON)  # Extracted topics/keywords

    # Conversation Threading
    conversation_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    is_first_message = Column(Boolean, default=True)
    parent_response_id = Column(UUID(as_uuid=True), ForeignKey("customer_responses.id"))
    thread_message_count = Column(Integer, default=1)

    # Assignment & Workflow
    status = Column(Enum(ResponseStatus), default=ResponseStatus.NEW, index=True)
    assigned_to = Column(String(255), index=True)
    assigned_at = Column(DateTime)
    team = Column(String(100))  # sales, support, success

    # SLA Tracking
    sla_target_minutes = Column(Integer)  # Target response time
    sla_breach_at = Column(DateTime)  # When SLA will be breached
    is_sla_breached = Column(Boolean, default=False)
    responded_within_sla = Column(Boolean)

    # AI Response Draft
    ai_suggested_response = Column(Text)
    ai_response_confidence = Column(Float)
    ai_reasoning = Column(String(1000))  # Why AI suggested this response

    # Human Response
    human_response = Column(Text)
    response_approved_at = Column(DateTime)
    response_approved_by = Column(String(255))
    response_sent_at = Column(DateTime)

    # Tags & Categorization
    tags = Column(JSON)  # Custom tags
    is_flagged = Column(Boolean, default=False)
    flag_reason = Column(String(500))

    # Next Best Action
    recommended_action = Column(String(255))  # What to do next
    recommended_followup_date = Column(DateTime)

    # Metadata
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    first_viewed_at = Column(DateTime)
    closed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    child_responses = relationship("CustomerResponse", backref="parent_response", remote_side=[id])
    ai_classifications = relationship("AIClassification", back_populates="response", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation thread grouping related messages."""
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Participants
    customer_id = Column(String(255), nullable=False, index=True)
    customer_name = Column(String(255))
    assigned_to = Column(String(255), index=True)

    # Conversation Details
    channel = Column(String(50), nullable=False)
    subject = Column(String(500))  # Thread subject
    message_count = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="active")  # active, waiting, closed
    last_message_at = Column(DateTime, index=True)
    last_message_from = Column(String(50))  # customer, agent, system

    # Classification
    primary_intent = Column(String(50))
    overall_sentiment = Column(Float)
    is_escalated = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    closed_at = Column(DateTime)


class ResponseTemplate(Base):
    """Pre-approved response templates."""
    __tablename__ = "response_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Template Details
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    category = Column(String(100), index=True)  # faq, objection_handling, follow_up, etc.

    # Applicability
    applicable_intents = Column(JSON)  # Which intents this template addresses
    applicable_channels = Column(JSON)  # Which channels it works for

    # Content
    subject_template = Column(String(500))
    body_template = Column(Text, nullable=False)
    variables = Column(JSON)  # Required/optional variables

    # Performance
    times_used = Column(Integer, default=0)
    avg_customer_satisfaction = Column(Float)
    avg_resolution_time_minutes = Column(Integer)

    # Status
    is_active = Column(Boolean, default=True)
    requires_approval = Column(Boolean, default=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))


class AIClassification(Base):
    """Detailed AI classification results for responses."""
    __tablename__ = "ai_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    response_id = Column(UUID(as_uuid=True), ForeignKey("customer_responses.id"), nullable=False, index=True)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Classification Results
    intent = Column(String(100), nullable=False)
    intent_confidence = Column(Float, nullable=False)
    sentiment_score = Column(Float)
    sentiment_label = Column(String(50))  # positive, negative, neutral
    urgency = Column(String(50))

    # Extracted Entities
    entities = Column(JSON)  # Named entities, products mentioned, etc.
    topics = Column(JSON)  # Main topics discussed
    keywords = Column(JSON)  # Important keywords

    # Business Context
    purchase_intent_score = Column(Float)  # 0.0-1.0
    churn_risk_score = Column(Float)  # 0.0-1.0
    satisfaction_score = Column(Float)  # 0.0-1.0

    # Suggested Actions
    recommended_response_template_id = Column(UUID(as_uuid=True))
    recommended_action = Column(String(255))
    reasoning = Column(String(2000))  # AI's reasoning

    # Model Info
    model_used = Column(String(100))
    model_version = Column(String(50))
    processing_time_ms = Column(Integer)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    response = relationship("CustomerResponse", back_populates="ai_classifications")
