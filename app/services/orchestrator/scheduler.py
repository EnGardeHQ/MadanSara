"""Scheduler - Optimize send times and manage daily message limits."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, time
from uuid import UUID
from sqlalchemy.orm import Session
import pytz

from app.models.outreach import OutreachCampaign, OutreachMessage, OutreachStatus


class SendTimeScheduler:
    """Schedules messages for optimal send times based on multiple factors."""

    def __init__(self, db: Session):
        self.db = db

    async def get_optimal_send_time(
        self,
        campaign: OutreachCampaign,
        recipient_profile: Dict[str, Any],
        channel: str,
    ) -> datetime:
        """
        Calculate optimal send time for a message.

        Args:
            campaign: Campaign instance
            recipient_profile: Recipient data including timezone, behavior
            channel: Channel to send on

        Returns:
            Optimal datetime to send
        """
        # If campaign has send time optimization disabled, send immediately
        if not campaign.send_time_optimization:
            return datetime.utcnow()

        # Get recipient's timezone (default to UTC)
        recipient_tz = recipient_profile.get("timezone", "UTC")
        try:
            tz = pytz.timezone(recipient_tz)
        except:
            tz = pytz.UTC

        # Get current time in recipient's timezone
        now_recipient = datetime.now(tz)

        # Check if we have learned optimal times for this campaign
        if campaign.optimal_send_times:
            learned_time = self._get_learned_optimal_time(
                campaign.optimal_send_times, channel, recipient_profile
            )
            if learned_time:
                return self._next_occurrence_of_time(learned_time, tz)

        # Fall back to channel-specific best practices
        optimal_time = self._get_channel_optimal_time(channel, recipient_profile)

        return self._next_occurrence_of_time(optimal_time, tz)

    def _get_learned_optimal_time(
        self,
        optimal_times: Dict[str, Any],
        channel: str,
        recipient_profile: Dict[str, Any],
    ) -> Optional[time]:
        """Get learned optimal time from campaign data."""
        # optimal_times format: {"email": {"weekday": "14:00", "weekend": "10:00"}, ...}
        channel_times = optimal_times.get(channel, {})

        if not channel_times:
            return None

        # Determine if today is weekday or weekend
        today = datetime.now().weekday()  # 0=Monday, 6=Sunday
        is_weekend = today >= 5

        time_str = channel_times.get("weekend" if is_weekend else "weekday")

        if time_str:
            try:
                hour, minute = map(int, time_str.split(":"))
                return time(hour=hour, minute=minute)
            except:
                return None

        return None

    def _get_channel_optimal_time(
        self, channel: str, recipient_profile: Dict[str, Any]
    ) -> time:
        """Get default optimal time for channel based on best practices."""
        customer_type = recipient_profile.get("customer_type", "new")

        # Best practice send times by channel and customer type
        optimal_times = {
            "email": {
                "new": time(10, 0),  # 10:00 AM - professional hours
                "returning": time(14, 0),  # 2:00 PM - afternoon
                "existing": time(9, 0),  # 9:00 AM - early morning
            },
            "instagram": {
                "new": time(19, 0),  # 7:00 PM - evening engagement
                "returning": time(20, 0),  # 8:00 PM - peak evening
                "existing": time(18, 0),  # 6:00 PM - after work
            },
            "facebook": {
                "new": time(19, 0),  # 7:00 PM
                "returning": time(20, 0),  # 8:00 PM
                "existing": time(18, 0),  # 6:00 PM
            },
            "linkedin": {
                "new": time(11, 0),  # 11:00 AM - mid-morning
                "returning": time(13, 0),  # 1:00 PM - lunch time
                "existing": time(10, 0),  # 10:00 AM - business hours
            },
            "twitter": {
                "new": time(12, 0),  # 12:00 PM - lunch hour
                "returning": time(17, 0),  # 5:00 PM - commute time
                "existing": time(15, 0),  # 3:00 PM - afternoon
            },
            "whatsapp": {
                "new": time(18, 0),  # 6:00 PM - avoid being intrusive
                "returning": time(19, 0),  # 7:00 PM
                "existing": time(10, 0),  # 10:00 AM - established relationship
            },
            "chat": {
                "new": time(14, 0),  # 2:00 PM - during browsing
                "returning": time(15, 0),  # 3:00 PM
                "existing": time(13, 0),  # 1:00 PM
            },
        }

        return optimal_times.get(channel, {}).get(
            customer_type, time(10, 0)  # Default to 10:00 AM
        )

    def _next_occurrence_of_time(
        self, target_time: time, timezone: pytz.timezone
    ) -> datetime:
        """Calculate next occurrence of a specific time in given timezone."""
        now = datetime.now(timezone)

        # Create datetime for today at target time
        target_datetime = datetime.combine(now.date(), target_time)
        target_datetime = timezone.localize(target_datetime)

        # If target time has passed today, schedule for tomorrow
        if target_datetime <= now:
            target_datetime += timedelta(days=1)

        # Convert to UTC for storage
        return target_datetime.astimezone(pytz.UTC).replace(tzinfo=None)

    async def check_daily_limit(
        self,
        campaign: OutreachCampaign,
        recipient_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Check if daily message limit has been reached.

        Args:
            campaign: Campaign instance
            recipient_id: Optional specific recipient

        Returns:
            Dict with can_send, messages_sent_today, daily_limit
        """
        if not campaign.daily_limit:
            return {
                "can_send": True,
                "messages_sent_today": 0,
                "daily_limit": None,
                "reason": "no_limit_set",
            }

        # Get messages sent today
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        query = self.db.query(OutreachMessage).filter(
            OutreachMessage.campaign_id == campaign.id,
            OutreachMessage.created_at >= today_start,
            OutreachMessage.status != OutreachStatus.FAILED,
        )

        if recipient_id:
            query = query.filter(OutreachMessage.recipient_id == recipient_id)

        messages_today = query.count()

        can_send = messages_today < campaign.daily_limit

        return {
            "can_send": can_send,
            "messages_sent_today": messages_today,
            "daily_limit": campaign.daily_limit,
            "remaining_today": max(0, campaign.daily_limit - messages_today),
            "reason": "within_limit" if can_send else "daily_limit_reached",
        }

    async def schedule_batch(
        self,
        campaign: OutreachCampaign,
        recipients: List[Dict[str, Any]],
        channel: str,
    ) -> List[Dict[str, Any]]:
        """
        Schedule a batch of messages across the day.

        Args:
            campaign: Campaign instance
            recipients: List of recipient profiles
            channel: Channel to send on

        Returns:
            List of scheduled send times for each recipient
        """
        scheduled = []

        # Check daily limit
        limit_check = await self.check_daily_limit(campaign)

        if not limit_check["can_send"]:
            return []

        available_slots = limit_check.get("remaining_today", len(recipients))

        # Limit batch to available slots
        recipients_to_schedule = recipients[:available_slots]

        # Calculate spacing between sends (to avoid bursts)
        if len(recipients_to_schedule) > 1:
            # Space messages out over the day
            spacing_minutes = min(
                (24 * 60) // len(recipients_to_schedule), 30  # Max 30 min apart
            )
        else:
            spacing_minutes = 0

        base_time = datetime.utcnow()

        for i, recipient in enumerate(recipients_to_schedule):
            # Get optimal time for this recipient
            optimal_time = await self.get_optimal_send_time(
                campaign, recipient, channel
            )

            # Add spacing to avoid sending all at once
            if spacing_minutes > 0:
                send_time = optimal_time + timedelta(minutes=i * spacing_minutes)
            else:
                send_time = optimal_time

            scheduled.append({
                "recipient_id": recipient.get("id"),
                "scheduled_at": send_time,
                "reason": "optimal_time_with_spacing",
            })

        return scheduled

    async def get_send_time_analytics(
        self,
        campaign_id: UUID,
        channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get analytics on send times and their performance."""
        query = self.db.query(OutreachMessage).filter(
            OutreachMessage.campaign_id == campaign_id,
            OutreachMessage.sent_at.isnot(None),
        )

        if channel:
            query = query.filter(OutreachMessage.channel == channel)

        messages = query.all()

        if not messages:
            return {
                "total_messages": 0,
                "best_hour": None,
                "best_day": None,
                "performance_by_hour": {},
            }

        # Analyze by hour of day
        hour_stats = {}
        day_stats = {}

        for msg in messages:
            if not msg.sent_at:
                continue

            hour = msg.sent_at.hour
            day = msg.sent_at.strftime("%A")  # Monday, Tuesday, etc.

            # Initialize hour stats
            if hour not in hour_stats:
                hour_stats[hour] = {"sent": 0, "opened": 0, "clicked": 0, "replied": 0}

            hour_stats[hour]["sent"] += 1
            if msg.opened_at:
                hour_stats[hour]["opened"] += 1
            if msg.clicked_at:
                hour_stats[hour]["clicked"] += 1
            if msg.replied_at:
                hour_stats[hour]["replied"] += 1

            # Initialize day stats
            if day not in day_stats:
                day_stats[day] = {"sent": 0, "opened": 0, "clicked": 0, "replied": 0}

            day_stats[day]["sent"] += 1
            if msg.opened_at:
                day_stats[day]["opened"] += 1
            if msg.clicked_at:
                day_stats[day]["clicked"] += 1
            if msg.replied_at:
                day_stats[day]["replied"] += 1

        # Calculate rates and find best performers
        best_hour = None
        best_hour_rate = 0.0

        for hour, stats in hour_stats.items():
            if stats["sent"] > 0:
                open_rate = stats["opened"] / stats["sent"]
                if open_rate > best_hour_rate:
                    best_hour_rate = open_rate
                    best_hour = hour

        return {
            "total_messages": len(messages),
            "best_hour": best_hour,
            "best_hour_open_rate": round(best_hour_rate, 3),
            "performance_by_hour": hour_stats,
            "performance_by_day": day_stats,
        }
