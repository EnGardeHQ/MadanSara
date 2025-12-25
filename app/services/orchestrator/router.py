"""Multi-channel router - Core orchestration logic for routing messages to optimal channels."""

from typing import List, Dict, Optional, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.outreach import OutreachMessage, OutreachCampaign, ChannelType


class ChannelRouter:
    """Routes outreach messages to the optimal channel based on multiple factors."""

    def __init__(self, db: Session):
        self.db = db

    async def route_message(
        self,
        campaign: OutreachCampaign,
        recipient_id: str,
        available_channels: List[str],
        recipient_preferences: Optional[Dict[str, Any]] = None,
        recipient_contact_info: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Route a message to the optimal channel.

        Args:
            campaign: The outreach campaign
            recipient_id: Unique recipient identifier
            available_channels: List of channels enabled for this campaign
            recipient_preferences: User's channel preferences
            recipient_contact_info: Contact information (email, phone, social handles)

        Returns:
            Dict with selected_channel, reason, and fallback_channels
        """
        # Step 1: Filter channels by availability and contact info
        viable_channels = self._filter_viable_channels(
            available_channels, recipient_contact_info
        )

        if not viable_channels:
            return {
                "selected_channel": None,
                "reason": "no_viable_channels",
                "error": "No channels available with valid contact information",
            }

        # Step 2: Apply recipient preferences
        preferred_channel = self._check_user_preference(
            viable_channels, recipient_preferences
        )

        if preferred_channel:
            return {
                "selected_channel": preferred_channel,
                "reason": "user_preference",
                "fallback_channels": self._order_fallback_channels(
                    viable_channels, exclude=preferred_channel
                ),
            }

        # Step 3: Apply campaign channel priority
        prioritized_channel = self._apply_campaign_priority(
            campaign, viable_channels
        )

        if prioritized_channel:
            return {
                "selected_channel": prioritized_channel,
                "reason": "campaign_priority",
                "fallback_channels": self._order_fallback_channels(
                    viable_channels, exclude=prioritized_channel
                ),
            }

        # Step 4: Use channel performance data
        best_performing_channel = await self._select_by_performance(
            campaign.tenant_uuid, viable_channels, recipient_id
        )

        if best_performing_channel:
            return {
                "selected_channel": best_performing_channel,
                "reason": "performance_based",
                "fallback_channels": self._order_fallback_channels(
                    viable_channels, exclude=best_performing_channel
                ),
            }

        # Step 5: Default to first viable channel
        default_channel = viable_channels[0]
        return {
            "selected_channel": default_channel,
            "reason": "default_selection",
            "fallback_channels": viable_channels[1:],
        }

    def _filter_viable_channels(
        self, channels: List[str], contact_info: Optional[Dict[str, str]]
    ) -> List[str]:
        """Filter channels based on available contact information."""
        if not contact_info:
            return []

        viable = []

        # Email requires email address
        if "email" in channels and contact_info.get("email"):
            viable.append("email")

        # Instagram requires instagram handle
        if "instagram" in channels and contact_info.get("instagram_handle"):
            viable.append("instagram")

        # Facebook requires facebook id
        if "facebook" in channels and contact_info.get("facebook_id"):
            viable.append("facebook")

        # LinkedIn requires linkedin id
        if "linkedin" in channels and contact_info.get("linkedin_id"):
            viable.append("linkedin")

        # Twitter requires twitter handle
        if "twitter" in channels and contact_info.get("twitter_handle"):
            viable.append("twitter")

        # WhatsApp requires phone number
        if "whatsapp" in channels and contact_info.get("phone"):
            viable.append("whatsapp")

        # Chat requires user_id (for website chat)
        if "chat" in channels and contact_info.get("user_id"):
            viable.append("chat")

        return viable

    def _check_user_preference(
        self, viable_channels: List[str], preferences: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Check if user has expressed a channel preference."""
        if not preferences:
            return None

        preferred_channel = preferences.get("preferred_channel")

        # Only return preference if it's in viable channels
        if preferred_channel and preferred_channel in viable_channels:
            return preferred_channel

        return None

    def _apply_campaign_priority(
        self, campaign: OutreachCampaign, viable_channels: List[str]
    ) -> Optional[str]:
        """Apply campaign-level channel priority."""
        if not campaign.channel_priority:
            return None

        # channel_priority is a dict like: {"new": ["email", "instagram"], "returning": ["instagram", "email"]}
        # For now, use a default key or first available
        priority_list = campaign.channel_priority.get("default", [])

        for channel in priority_list:
            if channel in viable_channels:
                return channel

        return None

    async def _select_by_performance(
        self, tenant_uuid: UUID, viable_channels: List[str], recipient_id: str
    ) -> Optional[str]:
        """Select channel based on historical performance data."""
        # TODO: Query ChannelPerformance table to find best-performing channel
        # For now, implement a simple heuristic:
        # Email > Instagram > LinkedIn > Facebook > Twitter > WhatsApp > Chat

        performance_order = [
            "email",
            "instagram",
            "linkedin",
            "facebook",
            "twitter",
            "whatsapp",
            "chat",
        ]

        for channel in performance_order:
            if channel in viable_channels:
                return channel

        return None

    def _order_fallback_channels(
        self, viable_channels: List[str], exclude: str
    ) -> List[str]:
        """Order remaining channels as fallbacks."""
        return [ch for ch in viable_channels if ch != exclude]

    async def route_with_fallback(
        self,
        campaign: OutreachCampaign,
        recipient_id: str,
        available_channels: List[str],
        recipient_preferences: Optional[Dict[str, Any]] = None,
        recipient_contact_info: Optional[Dict[str, str]] = None,
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Route message with automatic fallback on failure.

        Args:
            campaign: Outreach campaign
            recipient_id: Recipient ID
            available_channels: Available channels
            recipient_preferences: User preferences
            recipient_contact_info: Contact information
            max_attempts: Maximum fallback attempts

        Returns:
            Routing result with fallback chain
        """
        routing = await self.route_message(
            campaign,
            recipient_id,
            available_channels,
            recipient_preferences,
            recipient_contact_info,
        )

        if not routing["selected_channel"]:
            return routing

        # Build fallback chain (limited to max_attempts)
        fallback_chain = [routing["selected_channel"]]
        fallback_chain.extend(routing["fallback_channels"][:max_attempts - 1])

        return {
            "primary_channel": routing["selected_channel"],
            "fallback_chain": fallback_chain,
            "routing_reason": routing["reason"],
            "total_attempts_allowed": len(fallback_chain),
        }

    async def get_routing_analytics(
        self, tenant_uuid: UUID, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """Get analytics on routing decisions."""
        # TODO: Query OutreachMessage table for routing analytics
        return {
            "total_routed": 0,
            "by_channel": {},
            "by_reason": {},
            "fallback_usage": 0,
            "success_rate_by_channel": {},
        }
