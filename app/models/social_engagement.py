"""Social media engagement and automation models."""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Float, ForeignKey, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class SocialPlatform(str, enum.Enum):
    """Supported social platforms."""
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    TIKTOK = "tiktok"


class EngagementType(str, enum.Enum):
    """Types of social engagement."""
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    SAVE = "save"
    REPOST = "repost"
    MENTION = "mention"
    TAG = "tag"


class SocialPost(Base):
    """Track tenant's social media posts."""
    __tablename__ = "social_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Platform
    platform = Column(Enum(SocialPlatform), nullable=False, index=True)
    platform_post_id = Column(String(255), nullable=False, unique=True)
    platform_account_id = Column(String(255), nullable=False)

    # Content
    caption = Column(Text)
    post_type = Column(String(50))  # photo, video, carousel, story, reel
    media_urls = Column(JSON)  # URLs to media files
    hashtags = Column(JSON)  # List of hashtags used

    # Engagement Stats
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    saves_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    reach = Column(Integer)
    impressions = Column(Integer)

    # Calculated Metrics
    engagement_rate = Column(Float)  # (likes + comments + shares) / reach
    engagement_score = Column(Float)  # Weighted score: save(10) + share(8) + comment(6) + like(2)

    # Automation Settings
    auto_respond_enabled = Column(Boolean, default=False)
    dm_funnel_enabled = Column(Boolean, default=False)
    keyword_triggers = Column(JSON)  # Keywords that trigger DM automation

    # Metadata
    posted_at = Column(DateTime, nullable=False, index=True)
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    engagements = relationship("SocialEngagement", back_populates="post", cascade="all, delete-orphan")


class SocialEngagement(Base):
    """Track individual engagement events on social posts."""
    __tablename__ = "social_engagements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)
    post_id = Column(UUID(as_uuid=True), ForeignKey("social_posts.id"), nullable=False, index=True)

    # Platform
    platform = Column(Enum(SocialPlatform), nullable=False, index=True)
    platform_engagement_id = Column(String(255))

    # Engagement Details
    engagement_type = Column(Enum(EngagementType), nullable=False, index=True)
    comment_text = Column(Text)  # If engagement is a comment

    # User Who Engaged
    user_platform_id = Column(String(255), nullable=False, index=True)
    user_username = Column(String(255), index=True)
    user_display_name = Column(String(255))
    user_profile_url = Column(String(500))
    user_follower_count = Column(Integer)

    # Engagement Scoring
    engagement_weight = Column(Float)  # save=10, share=8, comment=6, like=2
    user_influence_score = Column(Float)  # Based on follower count, etc.

    # Sentiment (for comments)
    comment_sentiment = Column(Float)  # -1.0 to 1.0
    comment_intent = Column(String(100))  # question, compliment, objection, etc.

    # Automation Triggers
    triggered_auto_response = Column(Boolean, default=False)
    auto_response_sent_at = Column(DateTime)
    triggered_dm_funnel = Column(Boolean, default=False)
    dm_sent_at = Column(DateTime)
    dm_message_id = Column(UUID(as_uuid=True))  # Link to outreach message

    # Advocate Identification
    is_potential_advocate = Column(Boolean, default=False)
    advocate_score = Column(Float)  # Based on engagement history

    # Conversion Tracking
    converted = Column(Boolean, default=False)
    conversion_value = Column(Float)
    conversion_event_id = Column(UUID(as_uuid=True))

    # Metadata
    engaged_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    post = relationship("SocialPost", back_populates="engagements")


class SocialEngagementFunnel(Base):
    """Define automated engagement-to-DM-to-conversion funnels."""
    __tablename__ = "social_engagement_funnels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Funnel Configuration
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    platform = Column(Enum(SocialPlatform), nullable=False, index=True)

    # Trigger Conditions
    trigger_engagement_types = Column(JSON, nullable=False)  # ["comment", "save"]
    keyword_triggers = Column(JSON)  # Specific keywords in comments
    min_engagement_score = Column(Float)  # Minimum score to trigger
    min_follower_count = Column(Integer)  # Filter by user influence

    # Auto-Response (public comment reply)
    auto_response_enabled = Column(Boolean, default=True)
    auto_response_template = Column(Text)
    auto_response_delay_minutes = Column(Integer, default=5)

    # DM Funnel
    dm_enabled = Column(Boolean, default=True)
    dm_template_id = Column(UUID(as_uuid=True))
    dm_delay_minutes = Column(Integer, default=30)  # Wait before sending DM
    dm_personalization_rules = Column(JSON)

    # Follow-up Sequence
    followup_enabled = Column(Boolean, default=False)
    followup_sequence = Column(JSON)  # Array of follow-up messages

    # Filters
    exclude_previous_customers = Column(Boolean, default=False)
    exclude_replied_users = Column(Boolean, default=True)
    daily_limit = Column(Integer)  # Max DMs per day

    # Performance
    total_triggered = Column(Integer, default=0)
    total_responses_sent = Column(Integer, default=0)
    total_dms_sent = Column(Integer, default=0)
    total_conversions = Column(Integer, default=0)
    conversion_rate = Column(Float)

    # Status
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))


class SocialAdvocate(Base):
    """Track and nurture brand advocates."""
    __tablename__ = "social_advocates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Platform Identity
    platform = Column(Enum(SocialPlatform), nullable=False)
    platform_user_id = Column(String(255), nullable=False, index=True)
    username = Column(String(255), index=True)
    display_name = Column(String(255))
    profile_url = Column(String(500))

    # Influence Metrics
    follower_count = Column(Integer)
    following_count = Column(Integer)
    post_count = Column(Integer)
    avg_engagement_rate = Column(Float)

    # Engagement with Tenant
    total_engagements = Column(Integer, default=0)
    likes_given = Column(Integer, default=0)
    comments_given = Column(Integer, default=0)
    shares_given = Column(Integer, default=0)
    saves_given = Column(Integer, default=0)

    # Advocate Scoring
    advocate_score = Column(Float, nullable=False, index=True)  # 0-100
    # Calculated based on:
    # - Engagement frequency
    # - Engagement quality (saves > shares > comments > likes)
    # - Positive sentiment
    # - Influence (follower count)
    # - Consistency (regular engagement over time)

    advocate_tier = Column(String(50))  # bronze, silver, gold, platinum
    sentiment_score = Column(Float)  # Average sentiment of their comments

    # Relationship Status
    is_customer = Column(Boolean, default=False)
    customer_id = Column(String(255))
    lifetime_value = Column(Float, default=0.0)
    is_active_advocate = Column(Boolean, default=True)

    # Outreach
    last_contacted_at = Column(DateTime)
    total_dms_received = Column(Integer, default=0)
    dm_response_rate = Column(Float)

    # Special Treatment
    vip_status = Column(Boolean, default=False)
    custom_tags = Column(JSON)
    notes = Column(Text)

    # Activity Timeline
    first_engagement_at = Column(DateTime, index=True)
    last_engagement_at = Column(DateTime, index=True)
    days_since_last_engagement = Column(Integer)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlatformInsight(Base):
    """Store insights from platform APIs (Meta, LinkedIn, Twitter analytics)."""
    __tablename__ = "platform_insights"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)

    # Platform
    platform = Column(Enum(SocialPlatform), nullable=False, index=True)
    insight_type = Column(String(100), nullable=False)  # audience, content, timing, etc.

    # Time Period
    date = Column(DateTime, nullable=False, index=True)
    period = Column(String(50))  # daily, weekly, monthly

    # Insight Data
    insight_data = Column(JSON, nullable=False)
    # Examples:
    # Audience: {"age_range": "25-34", "gender": "F", "top_location": "NYC"}
    # Best time: {"day": "Tuesday", "hour": 14, "engagement_rate": 0.08}
    # Content type: {"type": "video", "avg_engagement": 250}

    # Key Metrics
    key_metric_name = Column(String(100))
    key_metric_value = Column(Float)
    comparison_to_previous = Column(Float)  # % change

    # Recommendations
    recommendation = Column(Text)
    confidence_score = Column(Float)  # 0.0-1.0

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)
