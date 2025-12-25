"""Outreach campaign and message tracking models."""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Enum, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ChannelType(str, enum.Enum):
    """Supported outreach channels."""
    EMAIL = "email"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    WHATSAPP = "whatsapp"
    CHAT = "chat"


class OutreachStatus(str, enum.Enum):
    """Outreach message status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"


class OutreachCampaign(Base):
    """Multi-channel outreach campaign."""
    __tablename__ = "outreach_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Campaign Details
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    campaign_type = Column(String(50))  # newsletter, promotion, customer_service, etc.

    # Channel Configuration
    channels = Column(JSON, nullable=False)  # ["email", "instagram", "linkedin"]
    channel_priority = Column(JSON)  # Channel preference order per segment

    # Targeting
    audience_segment_id = Column(UUID(as_uuid=True), index=True)
    audience_filters = Column(JSON)  # Filters for dynamic segmentation

    # Budget & Pacing
    budget_total = Column(Float)
    budget_spent = Column(Float, default=0.0)
    budget_per_channel = Column(JSON)  # {"email": 100, "instagram": 50}
    daily_limit = Column(Integer)  # Max messages per day

    # Templates & Content
    templates = Column(JSON)  # {"email": "template_id", "instagram": "template_id"}
    personalization_rules = Column(JSON)  # Dynamic content rules

    # Scheduling
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    send_time_optimization = Column(Boolean, default=True)
    optimal_send_times = Column(JSON)  # Per segment/channel

    # Status & Stats
    status = Column(String(50), default="draft")  # draft, active, paused, completed
    total_recipients = Column(Integer, default=0)
    messages_sent = Column(Integer, default=0)
    messages_delivered = Column(Integer, default=0)
    messages_opened = Column(Integer, default=0)
    messages_clicked = Column(Integer, default=0)
    messages_replied = Column(Integer, default=0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))

    # Relationships
    messages = relationship("OutreachMessage", back_populates="campaign", cascade="all, delete-orphan")


class OutreachMessage(Base):
    """Individual outreach message sent via specific channel."""
    __tablename__ = "outreach_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("outreach_campaigns.id"), nullable=False, index=True)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Recipient
    recipient_id = Column(String(255), nullable=False, index=True)  # User/prospect ID
    recipient_email = Column(String(255))
    recipient_phone = Column(String(50))
    recipient_social_handle = Column(String(255))
    recipient_name = Column(String(255))

    # Channel
    channel = Column(Enum(ChannelType), nullable=False, index=True)
    channel_message_id = Column(String(255))  # External platform message ID

    # Content
    subject = Column(String(500))  # For email
    content = Column(String(5000), nullable=False)
    content_html = Column(String(10000))  # For email
    template_id = Column(String(255))
    personalization_data = Column(JSON)  # Variables used in template

    # Orchestration
    is_primary_channel = Column(Boolean, default=False)
    fallback_from_channel = Column(String(50))  # If this is a fallback message
    deduplication_key = Column(String(255), index=True)  # Prevent duplicate sends

    # Status & Timing
    status = Column(Enum(OutreachStatus), default=OutreachStatus.PENDING, index=True)
    scheduled_at = Column(DateTime)
    sent_at = Column(DateTime)
    delivered_at = Column(DateTime)
    opened_at = Column(DateTime)
    clicked_at = Column(DateTime)
    replied_at = Column(DateTime)

    # Engagement Tracking
    open_count = Column(Integer, default=0)
    click_count = Column(Integer, default=0)
    links_clicked = Column(JSON)  # Track which links were clicked

    # Response Handling
    has_response = Column(Boolean, default=False)
    response_sentiment = Column(Float)  # -1.0 to 1.0
    response_intent = Column(String(50))  # purchase, question, objection, etc.

    # HITL Approval
    requires_approval = Column(Boolean, default=False)
    approved_at = Column(DateTime)
    approved_by = Column(String(255))
    rejection_reason = Column(String(1000))

    # Error Handling
    error_message = Column(String(1000))
    retry_count = Column(Integer, default=0)
    last_retry_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campaign = relationship("OutreachCampaign", back_populates="messages")


class ChannelTemplate(Base):
    """Reusable content templates for each channel."""
    __tablename__ = "channel_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Template Details
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    channel = Column(Enum(ChannelType), nullable=False, index=True)
    category = Column(String(100))  # newsletter, welcome, promotion, etc.

    # Content
    subject_template = Column(String(500))  # For email
    content_template = Column(String(10000), nullable=False)
    html_template = Column(String(20000))  # For email
    variables = Column(JSON)  # List of required/optional variables

    # Performance (from best practices)
    avg_open_rate = Column(Float)
    avg_click_rate = Column(Float)
    avg_reply_rate = Column(Float)
    total_sent = Column(Integer, default=0)

    # A/B Testing
    is_control = Column(Boolean, default=False)
    ab_test_variants = Column(JSON)  # References to variant templates

    # Approval & Status
    status = Column(String(50), default="draft")  # draft, active, archived
    last_used_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
