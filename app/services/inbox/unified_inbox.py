"""Unified Inbox - Aggregates responses from all channels."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from app.models.responses import CustomerResponse, ResponseStatus, ResponseIntent, ResponseUrgency


class UnifiedInboxService:
    """Manages unified inbox across all communication channels."""

    def __init__(self, db: Session):
        self.db = db

    async def get_inbox(
        self,
        tenant_uuid: UUID,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "received_at",
        sort_order: str = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Get unified inbox messages.

        Args:
            tenant_uuid: Tenant UUID
            filters: Optional filters (status, channel, intent, assigned_to, etc.)
            sort_by: Field to sort by
            sort_order: asc or desc
            skip: Pagination offset
            limit: Page size

        Returns:
            Inbox messages and metadata
        """
        query = self.db.query(CustomerResponse).filter(
            CustomerResponse.tenant_uuid == tenant_uuid
        )

        # Apply filters
        if filters:
            if "status" in filters:
                query = query.filter(CustomerResponse.status == filters["status"])

            if "channel" in filters:
                query = query.filter(CustomerResponse.channel == filters["channel"])

            if "intent" in filters:
                query = query.filter(CustomerResponse.intent == filters["intent"])

            if "urgency" in filters:
                query = query.filter(CustomerResponse.urgency == filters["urgency"])

            if "assigned_to" in filters:
                query = query.filter(CustomerResponse.assigned_to == filters["assigned_to"])

            if "is_flagged" in filters:
                query = query.filter(CustomerResponse.is_flagged == filters["is_flagged"])

            if "sla_breached" in filters:
                query = query.filter(CustomerResponse.is_sla_breached == filters["sla_breached"])

        # Apply sorting
        if sort_order == "desc":
            query = query.order_by(desc(getattr(CustomerResponse, sort_by)))
        else:
            query = query.order_by(getattr(CustomerResponse, sort_by))

        # Get total count
        total = query.count()

        # Paginate
        messages = query.offset(skip).limit(limit).all()

        # Calculate unread count
        unread_count = self.db.query(CustomerResponse).filter(
            and_(
                CustomerResponse.tenant_uuid == tenant_uuid,
                CustomerResponse.status == ResponseStatus.NEW,
            )
        ).count()

        # Calculate SLA breach count
        sla_breach_count = self.db.query(CustomerResponse).filter(
            and_(
                CustomerResponse.tenant_uuid == tenant_uuid,
                CustomerResponse.is_sla_breached == True,
            )
        ).count()

        return {
            "messages": [self._format_message(msg) for msg in messages],
            "total": total,
            "unread_count": unread_count,
            "sla_breach_count": sla_breach_count,
            "page": skip // limit + 1,
            "pages": (total + limit - 1) // limit,
        }

    def _format_message(self, message: CustomerResponse) -> Dict[str, Any]:
        """Format message for API response."""
        return {
            "id": str(message.id),
            "customer_id": message.customer_id,
            "customer_name": message.customer_name,
            "customer_email": message.customer_email,
            "channel": message.channel,
            "subject": message.subject,
            "message_preview": message.message_body[:100] if message.message_body else "",
            "intent": message.intent.value if message.intent else None,
            "sentiment": message.sentiment_score,
            "urgency": message.urgency.value if message.urgency else None,
            "status": message.status.value,
            "assigned_to": message.assigned_to,
            "is_flagged": message.is_flagged,
            "is_sla_breached": message.is_sla_breached,
            "received_at": message.received_at.isoformat() if message.received_at else None,
            "first_viewed_at": message.first_viewed_at.isoformat() if message.first_viewed_at else None,
        }

    async def assign_message(
        self,
        response_id: UUID,
        assigned_to: str,
        team: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Assign message to team member.

        Args:
            response_id: Response ID
            assigned_to: User ID to assign to
            team: Optional team name

        Returns:
            Assignment result
        """
        message = self.db.query(CustomerResponse).filter(
            CustomerResponse.id == response_id
        ).first()

        if not message:
            return {"success": False, "error": "Message not found"}

        message.assigned_to = assigned_to
        message.assigned_at = datetime.utcnow()

        if team:
            message.team = team

        message.status = ResponseStatus.ASSIGNED

        self.db.commit()

        return {
            "success": True,
            "message_id": str(response_id),
            "assigned_to": assigned_to,
            "team": team,
        }

    async def mark_as_read(
        self,
        response_id: UUID,
    ) -> Dict[str, Any]:
        """Mark message as read."""
        message = self.db.query(CustomerResponse).filter(
            CustomerResponse.id == response_id
        ).first()

        if not message:
            return {"success": False, "error": "Message not found"}

        if not message.first_viewed_at:
            message.first_viewed_at = datetime.utcnow()

        self.db.commit()

        return {"success": True}

    async def flag_message(
        self,
        response_id: UUID,
        reason: str,
    ) -> Dict[str, Any]:
        """Flag message for review."""
        message = self.db.query(CustomerResponse).filter(
            CustomerResponse.id == response_id
        ).first()

        if not message:
            return {"success": False, "error": "Message not found"}

        message.is_flagged = True
        message.flag_reason = reason

        self.db.commit()

        return {"success": True, "flagged": True, "reason": reason}

    async def get_conversation_thread(
        self,
        conversation_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Get all messages in a conversation thread."""
        messages = self.db.query(CustomerResponse).filter(
            CustomerResponse.conversation_id == conversation_id
        ).order_by(CustomerResponse.received_at).all()

        return [self._format_message(msg) for msg in messages]

    async def get_sla_alerts(
        self,
        tenant_uuid: UUID,
    ) -> List[Dict[str, Any]]:
        """Get messages approaching or breaching SLA."""
        now = datetime.utcnow()

        # Get messages breached or approaching breach (within 1 hour)
        approaching = []

        messages = self.db.query(CustomerResponse).filter(
            and_(
                CustomerResponse.tenant_uuid == tenant_uuid,
                CustomerResponse.status.in_([
                    ResponseStatus.NEW,
                    ResponseStatus.ASSIGNED,
                    ResponseStatus.IN_PROGRESS,
                ]),
                CustomerResponse.sla_breach_at.isnot(None),
            )
        ).all()

        for msg in messages:
            if msg.sla_breach_at <= now:
                approaching.append({
                    "message_id": str(msg.id),
                    "customer_name": msg.customer_name,
                    "status": "breached",
                    "breached_by_minutes": int((now - msg.sla_breach_at).total_seconds() / 60),
                })
            elif msg.sla_breach_at <= now + timedelta(hours=1):
                approaching.append({
                    "message_id": str(msg.id),
                    "customer_name": msg.customer_name,
                    "status": "approaching",
                    "minutes_remaining": int((msg.sla_breach_at - now).total_seconds() / 60),
                })

        return approaching

    async def get_inbox_analytics(
        self,
        tenant_uuid: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get inbox analytics."""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()

        query = self.db.query(CustomerResponse).filter(
            and_(
                CustomerResponse.tenant_uuid == tenant_uuid,
                CustomerResponse.received_at >= start_date,
                CustomerResponse.received_at <= end_date,
            )
        )

        messages = query.all()

        # Calculate metrics
        total_messages = len(messages)
        by_channel = {}
        by_intent = {}
        by_urgency = {}
        avg_response_time = 0
        sla_compliance_rate = 0

        for msg in messages:
            # By channel
            channel = msg.channel
            by_channel[channel] = by_channel.get(channel, 0) + 1

            # By intent
            if msg.intent:
                intent = msg.intent.value
                by_intent[intent] = by_intent.get(intent, 0) + 1

            # By urgency
            if msg.urgency:
                urgency = msg.urgency.value
                by_urgency[urgency] = by_urgency.get(urgency, 0) + 1

        # Calculate SLA compliance
        sla_eligible = [m for m in messages if m.sla_target_minutes]
        if sla_eligible:
            sla_met = [m for m in sla_eligible if m.responded_within_sla]
            sla_compliance_rate = len(sla_met) / len(sla_eligible) * 100

        return {
            "total_messages": total_messages,
            "by_channel": by_channel,
            "by_intent": by_intent,
            "by_urgency": by_urgency,
            "sla_compliance_rate": round(sla_compliance_rate, 2),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
        }
