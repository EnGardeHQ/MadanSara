"""Channel selector - Intelligent channel selection based on recipient attributes and context."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session


class ChannelSelector:
    """Selects optimal channel based on recipient profile, behavior, and context."""

    def __init__(self, db: Session):
        self.db = db

    async def select_channel(
        self,
        recipient_profile: Dict[str, Any],
        available_channels: List[str],
        campaign_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Intelligently select channel based on multiple factors.

        Args:
            recipient_profile: User profile data including:
                - customer_type: new, returning, existing
                - engagement_history: Past engagement data
                - demographics: Age, location, etc.
                - device_preference: mobile, desktop
            available_channels: Channels available for this campaign
            campaign_context: Campaign type, urgency, etc.

        Returns:
            Dict with selected channel and confidence score
        """
        scores = {}

        for channel in available_channels:
            score = await self._calculate_channel_score(
                channel, recipient_profile, campaign_context
            )
            scores[channel] = score

        # Select channel with highest score
        if not scores:
            return {"channel": None, "confidence": 0.0, "reason": "no_channels"}

        best_channel = max(scores, key=scores.get)
        confidence = scores[best_channel]

        return {
            "channel": best_channel,
            "confidence": confidence,
            "all_scores": scores,
            "reason": self._get_selection_reason(
                best_channel, recipient_profile, campaign_context
            ),
        }

    async def _calculate_channel_score(
        self,
        channel: str,
        recipient_profile: Dict[str, Any],
        campaign_context: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate suitability score for a channel (0.0 to 1.0)."""
        score = 0.0

        # Factor 1: Customer type preference (0.3 weight)
        customer_type = recipient_profile.get("customer_type", "new")
        score += self._score_by_customer_type(channel, customer_type) * 0.3

        # Factor 2: Historical engagement (0.3 weight)
        engagement_history = recipient_profile.get("engagement_history", {})
        score += self._score_by_engagement(channel, engagement_history) * 0.3

        # Factor 3: Device preference (0.2 weight)
        device = recipient_profile.get("device_preference", "desktop")
        score += self._score_by_device(channel, device) * 0.2

        # Factor 4: Campaign urgency (0.1 weight)
        if campaign_context:
            urgency = campaign_context.get("urgency", "normal")
            score += self._score_by_urgency(channel, urgency) * 0.1

        # Factor 5: Time of day (0.1 weight)
        score += self._score_by_time(channel) * 0.1

        return min(score, 1.0)  # Cap at 1.0

    def _score_by_customer_type(self, channel: str, customer_type: str) -> float:
        """Score channel based on customer type."""
        # Mapping: higher score = better fit
        preferences = {
            "new": {
                "email": 0.9,  # New customers prefer less intrusive
                "instagram": 0.7,
                "facebook": 0.7,
                "linkedin": 0.6,
                "twitter": 0.5,
                "whatsapp": 0.4,  # More intrusive for new customers
                "chat": 0.8,
            },
            "returning": {
                "email": 0.8,
                "instagram": 0.9,  # Returning customers engage on social
                "facebook": 0.8,
                "linkedin": 0.7,
                "twitter": 0.7,
                "whatsapp": 0.6,
                "chat": 0.7,
            },
            "existing": {
                "email": 0.7,
                "instagram": 0.8,
                "facebook": 0.7,
                "linkedin": 0.8,
                "twitter": 0.6,
                "whatsapp": 0.9,  # Existing customers okay with direct
                "chat": 0.9,
            },
        }

        return preferences.get(customer_type, {}).get(channel, 0.5)

    def _score_by_engagement(
        self, channel: str, engagement_history: Dict[str, Any]
    ) -> float:
        """Score based on past engagement with this channel."""
        if not engagement_history:
            return 0.5  # Neutral if no history

        # Check open/click rates for this channel
        channel_stats = engagement_history.get(channel, {})

        open_rate = channel_stats.get("open_rate", 0.0)
        click_rate = channel_stats.get("click_rate", 0.0)
        reply_rate = channel_stats.get("reply_rate", 0.0)

        # Weighted average
        score = (open_rate * 0.3 + click_rate * 0.4 + reply_rate * 0.3)

        # If user has never engaged, penalize this channel
        if channel_stats.get("messages_sent", 0) > 0 and score == 0:
            return 0.2  # Low score for unresponsive channel

        return score

    def _score_by_device(self, channel: str, device: str) -> float:
        """Score based on typical device usage."""
        mobile_friendly = {
            "email": 0.7,
            "instagram": 1.0,  # Very mobile-friendly
            "facebook": 0.9,
            "linkedin": 0.6,
            "twitter": 0.9,
            "whatsapp": 1.0,  # Mobile-first
            "chat": 0.8,
        }

        desktop_friendly = {
            "email": 1.0,  # Desktop = detailed emails
            "instagram": 0.7,
            "facebook": 0.8,
            "linkedin": 1.0,  # Professional/desktop
            "twitter": 0.7,
            "whatsapp": 0.5,
            "chat": 0.9,
        }

        if device == "mobile":
            return mobile_friendly.get(channel, 0.5)
        elif device == "desktop":
            return desktop_friendly.get(channel, 0.5)
        else:
            return 0.5

    def _score_by_urgency(self, channel: str, urgency: str) -> float:
        """Score based on campaign urgency."""
        # Urgent messages work better on real-time channels
        urgency_fit = {
            "high": {
                "email": 0.5,
                "instagram": 0.7,
                "facebook": 0.7,
                "linkedin": 0.4,
                "twitter": 0.8,
                "whatsapp": 1.0,  # Most immediate
                "chat": 1.0,
            },
            "normal": {
                "email": 1.0,
                "instagram": 0.8,
                "facebook": 0.8,
                "linkedin": 0.9,
                "twitter": 0.7,
                "whatsapp": 0.7,
                "chat": 0.8,
            },
            "low": {
                "email": 1.0,  # Email good for non-urgent
                "instagram": 0.9,
                "facebook": 0.9,
                "linkedin": 1.0,
                "twitter": 0.8,
                "whatsapp": 0.5,
                "chat": 0.6,
            },
        }

        return urgency_fit.get(urgency, {}).get(channel, 0.5)

    def _score_by_time(self, channel: str) -> float:
        """Score based on current time of day."""
        current_hour = datetime.now().hour

        # Different channels perform better at different times
        if 9 <= current_hour <= 17:  # Business hours
            if channel in ["email", "linkedin"]:
                return 1.0
            elif channel in ["instagram", "facebook", "twitter"]:
                return 0.6
            else:
                return 0.7

        elif 18 <= current_hour <= 22:  # Evening
            if channel in ["instagram", "facebook", "whatsapp"]:
                return 1.0
            elif channel == "email":
                return 0.7
            else:
                return 0.8

        else:  # Night/early morning
            # Email is safe anytime (sent, read later)
            if channel == "email":
                return 0.9
            else:
                return 0.3  # Don't send DMs at night

    def _get_selection_reason(
        self,
        channel: str,
        recipient_profile: Dict[str, Any],
        campaign_context: Optional[Dict[str, Any]],
    ) -> str:
        """Generate human-readable reason for channel selection."""
        customer_type = recipient_profile.get("customer_type", "unknown")
        device = recipient_profile.get("device_preference", "unknown")
        urgency = campaign_context.get("urgency", "normal") if campaign_context else "normal"

        reasons = []

        if customer_type == "existing" and channel in ["whatsapp", "chat"]:
            reasons.append("existing customer relationship allows direct messaging")

        if device == "mobile" and channel in ["instagram", "whatsapp"]:
            reasons.append("mobile user prefers mobile-first channels")

        if urgency == "high" and channel in ["whatsapp", "chat"]:
            reasons.append("urgent message requires immediate channel")

        if not reasons:
            reasons.append(f"best overall fit for {customer_type} customer")

        return "; ".join(reasons)

    async def get_channel_recommendations(
        self, tenant_uuid: UUID, customer_segment: str
    ) -> Dict[str, List[str]]:
        """Get recommended channels for different customer segments."""
        # TODO: Query performance data to generate data-driven recommendations
        recommendations = {
            "new": ["email", "chat", "instagram"],
            "returning": ["instagram", "email", "facebook"],
            "existing": ["whatsapp", "chat", "email"],
        }

        return recommendations.get(customer_segment, ["email"])
