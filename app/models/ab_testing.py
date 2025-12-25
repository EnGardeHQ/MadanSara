"""A/B testing and experimentation models."""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class TestType(str, enum.Enum):
    """Types of A/B tests."""
    BUTTON = "button"
    COPY = "copy"
    SUBJECT_LINE = "subject_line"
    SEND_TIME = "send_time"
    LAYOUT = "layout"
    CTA = "cta"
    IMAGE = "image"
    PERSONALIZATION = "personalization"


class TestStatus(str, enum.Enum):
    """A/B test status."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    WINNER_DECLARED = "winner_declared"


class ABTest(Base):
    """A/B test configuration and results."""
    __tablename__ = "ab_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Test Configuration
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    test_type = Column(Enum(TestType), nullable=False, index=True)
    hypothesis = Column(String(1000))

    # Targeting
    channel = Column(String(50), index=True)  # Which channel to test on
    campaign_id = Column(UUID(as_uuid=True), index=True)
    audience_segment_id = Column(UUID(as_uuid=True))
    customer_segment = Column(String(100))  # new, returning, existing

    # Test Settings
    traffic_allocation = Column(Float, default=0.5)  # 0.5 = 50/50 split
    variant_count = Column(Integer, default=2)
    control_variant_id = Column(UUID(as_uuid=True))

    # Statistical Settings
    min_sample_size = Column(Integer, default=100)
    confidence_level = Column(Float, default=0.95)  # 95% confidence
    min_detectable_effect = Column(Float, default=0.10)  # 10% improvement
    max_duration_days = Column(Integer, default=14)

    # Success Metrics
    primary_metric = Column(String(100), nullable=False)  # click_rate, conversion_rate, etc.
    secondary_metrics = Column(JSON)  # ["open_rate", "revenue"]

    # Timing
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime)
    expected_completion_date = Column(DateTime)
    actual_completion_date = Column(DateTime)

    # Status & Results
    status = Column(Enum(TestStatus), default=TestStatus.DRAFT, index=True)
    current_sample_size = Column(Integer, default=0)
    is_statistically_significant = Column(Boolean, default=False)
    p_value = Column(Float)
    winning_variant_id = Column(UUID(as_uuid=True))
    improvement_percentage = Column(Float)  # Winner vs control

    # Automatic Winner Selection
    auto_select_winner = Column(Boolean, default=True)
    winner_rollout_percentage = Column(Float, default=1.0)  # 100% rollout

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))

    # Relationships
    variants = relationship("ABTestVariant", back_populates="test", cascade="all, delete-orphan")


class ABTestVariant(Base):
    """Individual variant in an A/B test."""
    __tablename__ = "ab_test_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("ab_tests.id"), nullable=False, index=True)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Variant Details
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    is_control = Column(Boolean, default=False)
    traffic_percentage = Column(Float, nullable=False)  # Allocated traffic

    # Content/Configuration
    variant_config = Column(JSON, nullable=False)  # What's different in this variant
    # Examples:
    # Button test: {"text": "Buy Now", "color": "#FF0000", "size": "large"}
    # Copy test: {"headline": "...", "body": "...", "cta": "..."}
    # Subject test: {"subject_line": "..."}

    # Performance Metrics
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)

    # Calculated Rates
    click_rate = Column(Float)
    conversion_rate = Column(Float)
    avg_order_value = Column(Float)

    # Statistical Significance (vs control)
    is_significant = Column(Boolean, default=False)
    p_value_vs_control = Column(Float)
    confidence_interval_lower = Column(Float)
    confidence_interval_upper = Column(Float)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    test = relationship("ABTest", back_populates="variants")


class WebsiteABTest(Base):
    """Website-specific A/B tests (buttons, copy, CTAs)."""
    __tablename__ = "website_ab_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Test Configuration
    name = Column(String(255), nullable=False)
    test_type = Column(Enum(TestType), nullable=False)
    page_url_pattern = Column(String(1000))  # Which pages to test on
    element_selector = Column(String(500))  # CSS selector for element

    # Targeting
    customer_segment = Column(String(100))  # new, returning, existing
    device_targeting = Column(JSON)  # ["desktop", "mobile"]
    geo_targeting = Column(JSON)  # Country/region filters

    # Variants
    control_config = Column(JSON, nullable=False)
    variant_configs = Column(JSON, nullable=False)  # Array of variant configurations

    # Results
    impressions_control = Column(Integer, default=0)
    impressions_variants = Column(JSON)  # {"variant_1": 100, "variant_2": 95}
    conversions_control = Column(Integer, default=0)
    conversions_variants = Column(JSON)

    # Winner
    winning_variant = Column(String(100))
    is_winner_deployed = Column(Boolean, default=False)
    deployed_at = Column(DateTime)

    # Status
    status = Column(Enum(TestStatus), default=TestStatus.DRAFT)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BestPractice(Base):
    """Learned best practices from A/B tests and performance data."""
    __tablename__ = "best_practices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Practice Details
    category = Column(String(100), nullable=False, index=True)  # email, button, copy, timing, etc.
    channel = Column(String(50), index=True)
    practice_type = Column(String(100))  # subject_line_formula, send_time, cta_placement, etc.

    # The Practice
    title = Column(String(255), nullable=False)
    description = Column(String(2000), nullable=False)
    recommendation = Column(JSON)  # Structured recommendation data

    # Evidence
    source = Column(String(50))  # ab_test, external_research, platform_api, llm_knowledge
    source_test_id = Column(UUID(as_uuid=True))  # If from A/B test
    confidence_score = Column(Float)  # 0.0-1.0
    sample_size = Column(Integer)

    # Performance Impact
    improvement_metric = Column(String(100))  # What it improves (click_rate, conversion_rate)
    improvement_percentage = Column(Float)  # How much it improves
    baseline_value = Column(Float)
    optimized_value = Column(Float)

    # Applicability
    applicable_segments = Column(JSON)  # Which customer segments
    applicable_contexts = Column(JSON)  # When to apply

    # Validation
    is_validated = Column(Boolean, default=False)
    validation_count = Column(Integer, default=0)
    last_validated_at = Column(DateTime)

    # Usage
    times_applied = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    avg_performance_when_used = Column(Float)

    # Deprecation
    is_deprecated = Column(Boolean, default=False)
    deprecated_reason = Column(String(1000))
    deprecated_at = Column(DateTime)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
