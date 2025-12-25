"""Website funnel tracking and optimization models."""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class WebsiteVisitor(Base):
    """Track unique website visitors and their journey."""
    __tablename__ = "website_visitors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Visitor Identity
    visitor_id = Column(String(255), nullable=False, unique=True, index=True)  # Cookie/tracking ID
    user_id = Column(String(255), index=True)  # If authenticated
    customer_type = Column(String(50), index=True)  # new, returning, existing

    # Attribution
    first_visit_source = Column(String(100))  # Acquisition channel
    first_visit_campaign = Column(String(255))
    first_visit_url = Column(String(1000))
    first_visit_referrer = Column(String(1000))
    utm_source = Column(String(255))
    utm_medium = Column(String(255))
    utm_campaign = Column(String(255))
    utm_content = Column(String(255))
    utm_term = Column(String(255))

    # Device & Browser
    device_type = Column(String(50))  # desktop, mobile, tablet
    browser = Column(String(100))
    browser_version = Column(String(50))
    os = Column(String(100))
    os_version = Column(String(50))
    screen_resolution = Column(String(50))

    # Location
    country = Column(String(100))
    region = Column(String(100))
    city = Column(String(100))
    timezone = Column(String(100))

    # Behavior Summary
    total_visits = Column(Integer, default=1)
    total_page_views = Column(Integer, default=0)
    total_time_on_site_seconds = Column(Integer, default=0)
    avg_session_duration_seconds = Column(Float)

    # Conversion
    has_converted = Column(Boolean, default=False)
    first_conversion_at = Column(DateTime)
    conversion_count = Column(Integer, default=0)
    lifetime_value = Column(Float, default=0.0)

    # Metadata
    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    last_seen_at = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship("WebsiteSession", back_populates="visitor", cascade="all, delete-orphan")


class WebsiteSession(Base):
    """Individual website session/visit."""
    __tablename__ = "website_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)
    visitor_id = Column(UUID(as_uuid=True), ForeignKey("website_visitors.id"), nullable=False, index=True)

    # Session Identity
    session_id = Column(String(255), nullable=False, unique=True, index=True)

    # Attribution (session-specific)
    source = Column(String(100))
    medium = Column(String(100))
    campaign = Column(String(255))
    referrer = Column(String(1000))
    landing_page = Column(String(1000))

    # Behavior
    page_view_count = Column(Integer, default=0)
    event_count = Column(Integer, default=0)
    duration_seconds = Column(Integer)
    bounce = Column(Boolean, default=False)  # Single page view

    # Funnel Progress
    funnel_stage_reached = Column(String(100))  # awareness, consideration, purchase, etc.
    max_funnel_depth = Column(Integer, default=0)

    # Conversion
    converted = Column(Boolean, default=False)
    conversion_value = Column(Float)
    conversion_event_id = Column(UUID(as_uuid=True))

    # Engagement Score
    engagement_score = Column(Float)  # Calculated based on behavior

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ended_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    visitor = relationship("WebsiteVisitor", back_populates="sessions")
    page_views = relationship("PageView", back_populates="session", cascade="all, delete-orphan")
    events = relationship("WebsiteEvent", back_populates="session", cascade="all, delete-orphan")


class PageView(Base):
    """Individual page view tracking."""
    __tablename__ = "page_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("website_sessions.id"), nullable=False, index=True)

    # Page Details
    url = Column(String(1000), nullable=False, index=True)
    path = Column(String(500), index=True)
    title = Column(String(500))
    referrer = Column(String(1000))

    # Funnel Stage
    funnel_stage = Column(String(100), index=True)  # homepage, product, cart, checkout, thank_you
    is_conversion_page = Column(Boolean, default=False)

    # Engagement
    time_on_page_seconds = Column(Integer)
    scroll_depth_percentage = Column(Float)  # How far down page
    interactions_count = Column(Integer, default=0)  # Clicks, form fills, etc.

    # A/B Test Exposure
    active_ab_tests = Column(JSON)  # Which A/B tests this page view was part of
    ab_test_variants = Column(JSON)  # Which variants were shown

    # Sequence
    view_order = Column(Integer)  # 1st, 2nd, 3rd page in session

    # Metadata
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("WebsiteSession", back_populates="page_views")


class WebsiteEvent(Base):
    """Track specific user interactions and events."""
    __tablename__ = "website_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("website_sessions.id"), nullable=False, index=True)

    # Event Details
    event_type = Column(String(100), nullable=False, index=True)  # click, form_submit, video_play, etc.
    event_category = Column(String(100))  # engagement, conversion, navigation
    event_action = Column(String(255))
    event_label = Column(String(255))

    # Target Element
    element_id = Column(String(255))  # DOM element ID
    element_class = Column(String(255))  # CSS class
    element_text = Column(String(500))  # Button/link text
    element_type = Column(String(100))  # button, link, form, etc.

    # Context
    page_url = Column(String(1000))
    page_title = Column(String(500))

    # A/B Test Context
    ab_test_id = Column(UUID(as_uuid=True), index=True)
    ab_test_variant = Column(String(100))

    # Event Value
    event_value = Column(Float)  # For events with monetary value
    event_data = Column(JSON)  # Additional event-specific data

    # Metadata
    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("WebsiteSession", back_populates="events")


class FunnelDefinition(Base):
    """Define conversion funnels to track."""
    __tablename__ = "funnel_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Funnel Details
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    funnel_type = Column(String(100))  # purchase, signup, booking, etc.

    # Stages (ordered)
    stages = Column(JSON, nullable=False)
    # Example: [
    #   {"name": "Homepage", "url_pattern": "/", "stage_order": 1},
    #   {"name": "Product Page", "url_pattern": "/products/*", "stage_order": 2},
    #   {"name": "Cart", "url_pattern": "/cart", "stage_order": 3},
    #   {"name": "Checkout", "url_pattern": "/checkout", "stage_order": 4},
    #   {"name": "Thank You", "url_pattern": "/thank-you", "stage_order": 5}
    # ]

    # Segmentation
    customer_segments = Column(JSON)  # Track separately for new/returning/existing

    # Goal
    goal_event_type = Column(String(100))  # What constitutes completion
    goal_value = Column(Float)  # Expected value of completion

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FunnelAnalytics(Base):
    """Aggregated funnel performance analytics."""
    __tablename__ = "funnel_analytics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)
    funnel_id = Column(UUID(as_uuid=True), index=True)

    # Dimensions
    date = Column(DateTime, nullable=False, index=True)  # Daily aggregation
    customer_segment = Column(String(100), index=True)
    source = Column(String(100))  # Traffic source
    device_type = Column(String(50))

    # Funnel Metrics (per stage)
    stage_metrics = Column(JSON, nullable=False)
    # Example: {
    #   "homepage": {"visitors": 1000, "conversion_rate": 0.60},
    #   "product": {"visitors": 600, "conversion_rate": 0.50},
    #   "cart": {"visitors": 300, "conversion_rate": 0.33},
    #   "checkout": {"visitors": 100, "conversion_rate": 0.80},
    #   "thank_you": {"visitors": 80, "conversion_rate": 1.0}
    # }

    # Overall Funnel
    total_entered = Column(Integer, default=0)
    total_completed = Column(Integer, default=0)
    overall_conversion_rate = Column(Float)
    avg_time_to_convert_minutes = Column(Float)

    # Drop-off Analysis
    highest_dropoff_stage = Column(String(100))
    highest_dropoff_rate = Column(Float)

    # Value
    total_value = Column(Float, default=0.0)
    avg_order_value = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class OptimizationRecommendation(Base):
    """AI-generated optimization recommendations."""
    __tablename__ = "optimization_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Recommendation Details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    recommendation_type = Column(String(100))  # funnel, content, layout, etc.

    # Problem Identified
    problem_area = Column(String(255))  # Where issue was found
    problem_description = Column(Text)
    impact_severity = Column(String(50))  # high, medium, low

    # Suggested Solution
    suggested_change = Column(Text, nullable=False)
    implementation_steps = Column(JSON)
    expected_improvement = Column(String(500))

    # Supporting Data
    evidence = Column(JSON)  # Data supporting the recommendation
    confidence_score = Column(Float)  # 0.0-1.0

    # A/B Test Suggestion
    suggested_ab_test_config = Column(JSON)
    estimated_sample_size = Column(Integer)
    estimated_duration_days = Column(Integer)

    # Status
    status = Column(String(50), default="pending")  # pending, accepted, rejected, implemented
    implemented_at = Column(DateTime)
    ab_test_id = Column(UUID(as_uuid=True))  # If A/B test was created

    # Results (if implemented)
    actual_improvement = Column(Float)
    roi = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_by = Column(String(255))
    reviewed_at = Column(DateTime)
