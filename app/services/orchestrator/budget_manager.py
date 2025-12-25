"""Budget manager - Track and enforce budget limits across campaigns and channels."""

from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.models.outreach import OutreachCampaign, OutreachMessage, OutreachStatus


class BudgetManager:
    """Manages budget allocation and pacing for outreach campaigns."""

    def __init__(self, db: Session):
        self.db = db

    async def check_budget_available(
        self,
        campaign: OutreachCampaign,
        channel: str,
        estimated_cost: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Check if budget is available for sending.

        Args:
            campaign: OutreachCampaign instance
            channel: Channel to send on
            estimated_cost: Estimated cost per message

        Returns:
            Dict with can_send, remaining_budget, reason
        """
        # Check total campaign budget
        if campaign.budget_total:
            total_available = campaign.budget_total - (campaign.budget_spent or 0.0)
            if total_available < estimated_cost:
                return {
                    "can_send": False,
                    "remaining_budget": total_available,
                    "reason": "campaign_budget_exceeded",
                    "budget_total": campaign.budget_total,
                    "budget_spent": campaign.budget_spent,
                }

        # Check channel-specific budget
        if campaign.budget_per_channel:
            channel_budget = campaign.budget_per_channel.get(channel, {})
            channel_total = channel_budget.get("total", 0.0)
            channel_spent = channel_budget.get("spent", 0.0)

            if channel_total > 0:
                channel_available = channel_total - channel_spent
                if channel_available < estimated_cost:
                    return {
                        "can_send": False,
                        "remaining_budget": channel_available,
                        "reason": "channel_budget_exceeded",
                        "channel": channel,
                        "channel_budget_total": channel_total,
                        "channel_budget_spent": channel_spent,
                    }

        return {
            "can_send": True,
            "remaining_budget": self._calculate_remaining_budget(campaign, channel),
            "reason": "budget_available",
        }

    def _calculate_remaining_budget(
        self, campaign: OutreachCampaign, channel: Optional[str] = None
    ) -> float:
        """Calculate remaining budget for campaign or specific channel."""
        # Total campaign budget remaining
        total_remaining = float("inf")
        if campaign.budget_total:
            total_remaining = campaign.budget_total - (campaign.budget_spent or 0.0)

        # Channel budget remaining
        if channel and campaign.budget_per_channel:
            channel_budget = campaign.budget_per_channel.get(channel, {})
            channel_total = channel_budget.get("total", 0.0)
            channel_spent = channel_budget.get("spent", 0.0)

            if channel_total > 0:
                channel_remaining = channel_total - channel_spent
                return min(total_remaining, channel_remaining)

        return total_remaining if total_remaining != float("inf") else 0.0

    async def record_spend(
        self,
        campaign_id: UUID,
        channel: str,
        amount: float,
    ) -> Dict[str, Any]:
        """
        Record spend for a campaign and channel.

        Args:
            campaign_id: Campaign UUID
            channel: Channel used
            amount: Amount spent

        Returns:
            Updated budget information
        """
        campaign = self.db.query(OutreachCampaign).filter(
            OutreachCampaign.id == campaign_id
        ).first()

        if not campaign:
            return {"error": "campaign_not_found"}

        # Update total campaign spend
        campaign.budget_spent = (campaign.budget_spent or 0.0) + amount

        # Update channel-specific spend
        if campaign.budget_per_channel is None:
            campaign.budget_per_channel = {}

        if channel not in campaign.budget_per_channel:
            campaign.budget_per_channel[channel] = {"total": 0.0, "spent": 0.0}

        campaign.budget_per_channel[channel]["spent"] = (
            campaign.budget_per_channel[channel].get("spent", 0.0) + amount
        )

        self.db.commit()

        return {
            "campaign_id": str(campaign_id),
            "total_spent": campaign.budget_spent,
            "channel_spent": campaign.budget_per_channel[channel]["spent"],
            "remaining_budget": self._calculate_remaining_budget(campaign, channel),
        }

    async def calculate_daily_budget(
        self,
        campaign: OutreachCampaign,
        channel: Optional[str] = None,
    ) -> float:
        """
        Calculate daily budget allocation based on campaign timeline.

        Args:
            campaign: Campaign instance
            channel: Optional channel to calculate for

        Returns:
            Daily budget amount
        """
        if not campaign.budget_total or not campaign.end_date:
            return 0.0

        # Calculate days remaining
        now = datetime.utcnow()
        if campaign.end_date <= now:
            return 0.0

        days_remaining = (campaign.end_date - now).days + 1

        # Calculate remaining budget
        remaining_budget = self._calculate_remaining_budget(campaign, channel)

        # Divide evenly across remaining days
        daily_budget = remaining_budget / max(days_remaining, 1)

        return round(daily_budget, 2)

    async def check_daily_spend_limit(
        self,
        campaign: OutreachCampaign,
        channel: str,
    ) -> Dict[str, Any]:
        """
        Check if daily spend limit has been reached.

        Args:
            campaign: Campaign instance
            channel: Channel to check

        Returns:
            Dict with can_send, daily_spent, daily_limit
        """
        daily_limit = await self.calculate_daily_budget(campaign, channel)

        # Get today's spend
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        messages_today = self.db.query(OutreachMessage).filter(
            and_(
                OutreachMessage.campaign_id == campaign.id,
                OutreachMessage.channel == channel,
                OutreachMessage.created_at >= today_start,
                OutreachMessage.status != OutreachStatus.FAILED,
            )
        ).all()

        # Calculate today's spend (assuming cost per message)
        # TODO: Get actual costs from pricing table
        cost_per_message = self._get_channel_cost(channel)
        daily_spent = len(messages_today) * cost_per_message

        can_send = daily_spent < daily_limit if daily_limit > 0 else True

        return {
            "can_send": can_send,
            "daily_spent": daily_spent,
            "daily_limit": daily_limit,
            "messages_sent_today": len(messages_today),
            "reason": "within_daily_limit" if can_send else "daily_limit_reached",
        }

    def _get_channel_cost(self, channel: str) -> float:
        """Get estimated cost per message for a channel."""
        # Typical costs (can be moved to config/database)
        costs = {
            "email": 0.001,  # SendGrid ~$0.001 per email
            "instagram": 0.0,  # Free (API rate limits)
            "facebook": 0.0,  # Free (API rate limits)
            "linkedin": 0.0,  # Free (API rate limits)
            "twitter": 0.0,  # Free (API rate limits)
            "whatsapp": 0.005,  # Twilio ~$0.005 per message
            "chat": 0.0,  # Free (own infrastructure)
        }
        return costs.get(channel, 0.0)

    async def get_budget_pacing_recommendation(
        self,
        campaign: OutreachCampaign,
    ) -> Dict[str, Any]:
        """
        Get pacing recommendations to stay within budget.

        Args:
            campaign: Campaign instance

        Returns:
            Pacing recommendations
        """
        if not campaign.budget_total or not campaign.end_date:
            return {
                "recommendation": "no_budget_constraints",
                "can_increase_pace": True,
            }

        # Calculate ideal vs actual pace
        now = datetime.utcnow()
        campaign_duration = (campaign.end_date - campaign.start_date).days
        elapsed_days = (now - campaign.start_date).days

        if campaign_duration <= 0:
            return {"recommendation": "campaign_ended", "can_increase_pace": False}

        # Ideal spend percentage = elapsed days / total days
        ideal_spend_pct = elapsed_days / campaign_duration

        # Actual spend percentage
        actual_spend_pct = (
            (campaign.budget_spent or 0.0) / campaign.budget_total
            if campaign.budget_total > 0
            else 0.0
        )

        # Determine recommendation
        if actual_spend_pct > ideal_spend_pct + 0.1:  # Overspending by 10%+
            recommendation = "reduce_pace"
            suggested_daily_messages = self._calculate_reduced_pace(campaign)
        elif actual_spend_pct < ideal_spend_pct - 0.1:  # Underspending by 10%+
            recommendation = "increase_pace"
            suggested_daily_messages = self._calculate_increased_pace(campaign)
        else:
            recommendation = "maintain_pace"
            suggested_daily_messages = campaign.daily_limit

        return {
            "recommendation": recommendation,
            "ideal_spend_pct": round(ideal_spend_pct, 2),
            "actual_spend_pct": round(actual_spend_pct, 2),
            "suggested_daily_messages": suggested_daily_messages,
            "days_remaining": (campaign.end_date - now).days,
            "budget_remaining": campaign.budget_total - (campaign.budget_spent or 0.0),
        }

    def _calculate_reduced_pace(self, campaign: OutreachCampaign) -> int:
        """Calculate reduced daily message limit."""
        if campaign.daily_limit:
            return max(int(campaign.daily_limit * 0.7), 1)  # Reduce by 30%
        return 50  # Default conservative limit

    def _calculate_increased_pace(self, campaign: OutreachCampaign) -> int:
        """Calculate increased daily message limit."""
        if campaign.daily_limit:
            return int(campaign.daily_limit * 1.3)  # Increase by 30%
        return 200  # Default increased limit

    async def get_budget_analytics(
        self,
        campaign_id: UUID,
    ) -> Dict[str, Any]:
        """Get budget utilization analytics for a campaign."""
        campaign = self.db.query(OutreachCampaign).filter(
            OutreachCampaign.id == campaign_id
        ).first()

        if not campaign:
            return {"error": "campaign_not_found"}

        # Get spend by channel
        spend_by_channel = campaign.budget_per_channel or {}

        # Calculate efficiency metrics
        total_messages = campaign.messages_sent or 0
        cost_per_message = (
            (campaign.budget_spent / total_messages)
            if total_messages > 0 and campaign.budget_spent
            else 0.0
        )

        # Calculate conversion cost (if we have conversion data)
        # TODO: Join with conversion events
        cost_per_conversion = 0.0

        return {
            "campaign_id": str(campaign_id),
            "budget_total": campaign.budget_total,
            "budget_spent": campaign.budget_spent or 0.0,
            "budget_remaining": (campaign.budget_total or 0.0) - (campaign.budget_spent or 0.0),
            "budget_utilization_pct": (
                ((campaign.budget_spent or 0.0) / campaign.budget_total * 100)
                if campaign.budget_total
                else 0.0
            ),
            "spend_by_channel": spend_by_channel,
            "messages_sent": total_messages,
            "cost_per_message": round(cost_per_message, 4),
            "cost_per_conversion": round(cost_per_conversion, 2),
        }
