"""Conversion tracking and attribution models."""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class ConversionEvent(Base):
    """Track all conversion events across channels and touchpoints."""
    __tablename__ = "conversion_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # User/Customer
    user_id = Column(String(255), nullable=False, index=True)
    customer_type = Column(String(50))  # new, returning, existing

    # Conversion Details
    event_type = Column(String(100), nullable=False, index=True)  # purchase, signup, booking, etc.
    event_value = Column(Float)  # Revenue or value
    event_currency = Column(String(10), default="USD")

    # Source Attribution
    source_channel = Column(String(50), index=True)  # Last-touch channel
    source_campaign_id = Column(UUID(as_uuid=True), index=True)
    source_message_id = Column(UUID(as_uuid=True), index=True)

    # Journey Tracking
    touchpoint_count = Column(Integer, default=1)
    journey_id = Column(UUID(as_uuid=True), index=True)  # Link all touchpoints
    time_to_conversion_minutes = Column(Integer)  # From first touch

    # Context
    landing_page_url = Column(String(1000))
    referrer_url = Column(String(1000))
    utm_source = Column(String(255))
    utm_medium = Column(String(255))
    utm_campaign = Column(String(255))
    utm_content = Column(String(255))
    utm_term = Column(String(255))

    # Device & Location
    device_type = Column(String(50))  # desktop, mobile, tablet
    browser = Column(String(100))
    os = Column(String(100))
    country = Column(String(100))
    region = Column(String(100))
    city = Column(String(100))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    extra_data = Column(JSON)  # Additional custom data

    # Relationships
    touchpoints = relationship("CustomerTouchpoint", back_populates="conversion_event")


class CustomerTouchpoint(Base):
    """Track every interaction in the customer journey."""
    __tablename__ = "customer_touchpoints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Journey
    journey_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    conversion_event_id = Column(UUID(as_uuid=True), ForeignKey("conversion_events.id"), index=True)

    # Touchpoint Details
    touchpoint_type = Column(String(100), nullable=False)  # email_open, link_click, page_view, etc.
    channel = Column(String(50), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), index=True)
    message_id = Column(UUID(as_uuid=True), index=True)

    # Timing
    touchpoint_order = Column(Integer, default=1)  # 1st, 2nd, 3rd touch, etc.
    minutes_since_first_touch = Column(Integer)
    minutes_since_last_touch = Column(Integer)

    # Content
    page_url = Column(String(1000))
    content_title = Column(String(500))
    cta_clicked = Column(String(255))

    # Attribution Weight (for multi-touch models)
    attribution_weight_linear = Column(Float)  # Equal weight
    attribution_weight_time_decay = Column(Float)  # Recent = higher
    attribution_weight_first_touch = Column(Float)  # First = 100%
    attribution_weight_last_touch = Column(Float)  # Last = 100%
    attribution_weight_position_based = Column(Float)  # First & last = higher

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    extra_data = Column(JSON)

    # Relationships
    conversion_event = relationship("ConversionEvent", back_populates="touchpoints")


class AttributionModel(Base):
    """Attribution model configurations and results."""
    __tablename__ = "attribution_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Model Configuration
    name = Column(String(255), nullable=False)
    model_type = Column(String(50), nullable=False)  # first-touch, last-touch, linear, time-decay, position-based
    description = Column(String(1000))

    # Time Decay Parameters
    decay_rate = Column(Float)  # For time-decay model (0-1)
    half_life_hours = Column(Integer)  # When weight = 0.5

    # Position-Based Parameters
    first_touch_weight = Column(Float)  # e.g., 0.40
    last_touch_weight = Column(Float)   # e.g., 0.40
    middle_touch_weight = Column(Float)  # e.g., 0.20 split among middle

    # Aggregated Results (updated periodically)
    total_conversions_analyzed = Column(Integer, default=0)
    total_revenue_attributed = Column(Float, default=0.0)
    channel_attribution = Column(JSON)  # {"email": 0.45, "instagram": 0.30, ...}
    campaign_attribution = Column(JSON)  # Per campaign

    # Performance Metrics
    avg_touchpoints_to_conversion = Column(Float)
    avg_time_to_conversion_hours = Column(Float)
    most_effective_channel = Column(String(50))
    most_effective_campaign_id = Column(UUID(as_uuid=True))

    # Status
    is_active = Column(Boolean, default=True)
    last_calculated_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChannelPerformance(Base):
    """Aggregate channel performance metrics over time."""
    __tablename__ = "channel_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Dimensions
    channel = Column(String(50), nullable=False, index=True)
    campaign_id = Column(UUID(as_uuid=True), index=True)
    date = Column(DateTime, nullable=False, index=True)  # Daily aggregation
    customer_segment = Column(String(100), index=True)

    # Volume Metrics
    messages_sent = Column(Integer, default=0)
    messages_delivered = Column(Integer, default=0)
    messages_opened = Column(Integer, default=0)
    messages_clicked = Column(Integer, default=0)
    messages_replied = Column(Integer, default=0)

    # Engagement Rates
    delivery_rate = Column(Float)  # delivered / sent
    open_rate = Column(Float)      # opened / delivered
    click_rate = Column(Float)     # clicked / opened
    reply_rate = Column(Float)     # replied / delivered

    # Conversion Metrics
    conversions = Column(Integer, default=0)
    conversion_rate = Column(Float)  # conversions / delivered
    revenue = Column(Float, default=0.0)
    avg_order_value = Column(Float)

    # Attribution Metrics (multi-touch)
    attributed_conversions = Column(Float)  # Can be fractional
    attributed_revenue = Column(Float)
    attribution_model_used = Column(String(50))

    # Cost & ROI
    cost = Column(Float, default=0.0)
    roi = Column(Float)  # (revenue - cost) / cost
    cost_per_conversion = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
