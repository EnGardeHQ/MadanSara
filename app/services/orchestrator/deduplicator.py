"""Deduplication - Prevent duplicate message sends across channels and campaigns."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.outreach import OutreachMessage, OutreachStatus


class MessageDeduplicator:
    """Prevents duplicate message sends to the same recipient."""

    def __init__(self, db: Session):
        self.db = db

    async def check_duplicate(
        self,
        tenant_uuid: UUID,
        recipient_id: str,
        campaign_id: Optional[UUID] = None,
        channels: Optional[List[str]] = None,
        lookback_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Check if a message would be a duplicate.

        Args:
            tenant_uuid: Tenant UUID
            recipient_id: Recipient identifier
            campaign_id: Optional campaign to check within
            channels: Optional list of channels to check
            lookback_hours: How far back to look for duplicates

        Returns:
            Dict with is_duplicate, reason, last_message_at, blocked_channels
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=lookback_hours)

        # Build query
        query = self.db.query(OutreachMessage).filter(
            and_(
                OutreachMessage.tenant_uuid == tenant_uuid,
                OutreachMessage.recipient_id == recipient_id,
                OutreachMessage.created_at >= cutoff_time,
                OutreachMessage.status.in_([
                    OutreachStatus.SENT,
                    OutreachStatus.DELIVERED,
                    OutreachStatus.OPENED,
                    OutreachStatus.CLICKED,
                    OutreachStatus.REPLIED,
                ])
            )
        )

        # Filter by campaign if specified
        if campaign_id:
            query = query.filter(OutreachMessage.campaign_id == campaign_id)

        # Filter by channels if specified
        if channels:
            query = query.filter(OutreachMessage.channel.in_(channels))

        recent_messages = query.order_by(OutreachMessage.created_at.desc()).all()

        if not recent_messages:
            return {
                "is_duplicate": False,
                "reason": "no_recent_messages",
                "last_message_at": None,
                "blocked_channels": [],
            }

        # Analyze recent messages
        last_message = recent_messages[0]
        blocked_channels = list(set([msg.channel.value for msg in recent_messages]))

        return {
            "is_duplicate": True,
            "reason": "recent_message_sent",
            "last_message_at": last_message.sent_at or last_message.created_at,
            "last_message_channel": last_message.channel.value,
            "blocked_channels": blocked_channels,
            "messages_in_period": len(recent_messages),
            "cooldown_remaining_hours": self._calculate_cooldown_remaining(
                last_message.created_at, lookback_hours
            ),
        }

    def _calculate_cooldown_remaining(
        self, last_sent_at: datetime, cooldown_hours: int
    ) -> float:
        """Calculate remaining cooldown time in hours."""
        if not last_sent_at:
            return 0.0

        elapsed = datetime.utcnow() - last_sent_at
        elapsed_hours = elapsed.total_seconds() / 3600

        remaining = max(0, cooldown_hours - elapsed_hours)
        return round(remaining, 2)

    async def get_safe_channels(
        self,
        tenant_uuid: UUID,
        recipient_id: str,
        all_channels: List[str],
        lookback_hours: int = 24,
    ) -> List[str]:
        """
        Get list of channels safe to use (no recent messages).

        Args:
            tenant_uuid: Tenant UUID
            recipient_id: Recipient ID
            all_channels: All available channels
            lookback_hours: Lookback period

        Returns:
            List of safe channels
        """
        duplicate_check = await self.check_duplicate(
            tenant_uuid, recipient_id, lookback_hours=lookback_hours
        )

        if not duplicate_check["is_duplicate"]:
            return all_channels

        blocked = duplicate_check["blocked_channels"]
        safe_channels = [ch for ch in all_channels if ch not in blocked]

        return safe_channels

    async def generate_dedup_key(
        self,
        tenant_uuid: UUID,
        recipient_id: str,
        campaign_id: UUID,
        channel: str,
    ) -> str:
        """
        Generate a deduplication key for message tracking.

        Format: {tenant_uuid}:{recipient_id}:{campaign_id}:{channel}:{date}
        """
        date_str = datetime.utcnow().strftime("%Y%m%d")
        return f"{tenant_uuid}:{recipient_id}:{campaign_id}:{channel}:{date_str}"

    async def check_cross_campaign_duplicate(
        self,
        tenant_uuid: UUID,
        recipient_id: str,
        content_hash: str,
        lookback_days: int = 7,
    ) -> Dict[str, Any]:
        """
        Check if similar content was sent across ANY campaign.

        Args:
            tenant_uuid: Tenant UUID
            recipient_id: Recipient ID
            content_hash: Hash of message content
            lookback_days: Days to look back

        Returns:
            Dict with is_duplicate and details
        """
        # TODO: Implement content hashing and similarity detection
        # For now, return safe default
        return {
            "is_duplicate": False,
            "reason": "content_hash_check_not_implemented",
            "similar_messages": [],
        }

    async def apply_frequency_cap(
        self,
        tenant_uuid: UUID,
        recipient_id: str,
        max_messages_per_day: int = 3,
        max_messages_per_week: int = 10,
    ) -> Dict[str, Any]:
        """
        Check if recipient has reached frequency cap.

        Args:
            tenant_uuid: Tenant UUID
            recipient_id: Recipient ID
            max_messages_per_day: Daily message limit
            max_messages_per_week: Weekly message limit

        Returns:
            Dict with can_send, messages_sent_today, messages_sent_week
        """
        # Count messages in last 24 hours
        day_cutoff = datetime.utcnow() - timedelta(days=1)
        messages_today = self.db.query(OutreachMessage).filter(
            and_(
                OutreachMessage.tenant_uuid == tenant_uuid,
                OutreachMessage.recipient_id == recipient_id,
                OutreachMessage.created_at >= day_cutoff,
                OutreachMessage.status != OutreachStatus.FAILED,
            )
        ).count()

        # Count messages in last 7 days
        week_cutoff = datetime.utcnow() - timedelta(days=7)
        messages_week = self.db.query(OutreachMessage).filter(
            and_(
                OutreachMessage.tenant_uuid == tenant_uuid,
                OutreachMessage.recipient_id == recipient_id,
                OutreachMessage.created_at >= week_cutoff,
                OutreachMessage.status != OutreachStatus.FAILED,
            )
        ).count()

        can_send = (
            messages_today < max_messages_per_day
            and messages_week < max_messages_per_week
        )

        return {
            "can_send": can_send,
            "messages_sent_today": messages_today,
            "messages_sent_week": messages_week,
            "daily_limit": max_messages_per_day,
            "weekly_limit": max_messages_per_week,
            "reason": self._get_frequency_cap_reason(
                can_send, messages_today, messages_week, max_messages_per_day, max_messages_per_week
            ),
        }

    def _get_frequency_cap_reason(
        self,
        can_send: bool,
        today: int,
        week: int,
        daily_limit: int,
        weekly_limit: int,
    ) -> str:
        """Generate reason for frequency cap decision."""
        if can_send:
            return f"within limits ({today}/{daily_limit} today, {week}/{weekly_limit} this week)"

        if today >= daily_limit:
            return f"daily limit reached ({today}/{daily_limit})"

        if week >= weekly_limit:
            return f"weekly limit reached ({week}/{weekly_limit})"

        return "frequency cap applied"

    async def get_recipient_message_history(
        self,
        tenant_uuid: UUID,
        recipient_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get recent message history for a recipient."""
        messages = (
            self.db.query(OutreachMessage)
            .filter(
                and_(
                    OutreachMessage.tenant_uuid == tenant_uuid,
                    OutreachMessage.recipient_id == recipient_id,
                )
            )
            .order_by(OutreachMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": str(msg.id),
                "channel": msg.channel.value,
                "status": msg.status.value,
                "sent_at": msg.sent_at,
                "created_at": msg.created_at,
                "campaign_id": str(msg.campaign_id),
            }
            for msg in messages
        ]
