"""Database models for Madan Sara."""

from app.models.outreach import (
    OutreachCampaign,
    OutreachMessage,
    ChannelTemplate,
    ChannelType,
    OutreachStatus,
)
from app.models.conversion import (
    ConversionEvent,
    CustomerTouchpoint,
    AttributionModel,
    ChannelPerformance,
)
from app.models.ab_testing import (
    ABTest,
    ABTestVariant,
    WebsiteABTest,
    BestPractice,
    TestType,
    TestStatus,
)
from app.models.responses import (
    CustomerResponse,
    Conversation,
    ResponseTemplate,
    AIClassification,
    ResponseStatus,
    ResponseIntent,
    ResponseUrgency,
)
from app.models.website_optimization import (
    WebsiteVisitor,
    WebsiteSession,
    PageView,
    WebsiteEvent,
    FunnelDefinition,
    FunnelAnalytics,
    OptimizationRecommendation,
)
from app.models.social_engagement import (
    SocialPost,
    SocialEngagement,
    SocialEngagementFunnel,
    SocialAdvocate,
    PlatformInsight,
    SocialPlatform,
    EngagementType,
)

__all__ = [
    # Outreach
    "OutreachCampaign",
    "OutreachMessage",
    "ChannelTemplate",
    "ChannelType",
    "OutreachStatus",
    # Conversion
    "ConversionEvent",
    "CustomerTouchpoint",
    "AttributionModel",
    "ChannelPerformance",
    # A/B Testing
    "ABTest",
    "ABTestVariant",
    "WebsiteABTest",
    "BestPractice",
    "TestType",
    "TestStatus",
    # Responses
    "CustomerResponse",
    "Conversation",
    "ResponseTemplate",
    "AIClassification",
    "ResponseStatus",
    "ResponseIntent",
    "ResponseUrgency",
    # Website Optimization
    "WebsiteVisitor",
    "WebsiteSession",
    "PageView",
    "WebsiteEvent",
    "FunnelDefinition",
    "FunnelAnalytics",
    "OptimizationRecommendation",
    # Social Engagement
    "SocialPost",
    "SocialEngagement",
    "SocialEngagementFunnel",
    "SocialAdvocate",
    "PlatformInsight",
    "SocialPlatform",
    "EngagementType",
]
