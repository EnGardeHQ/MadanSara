"""Unit tests for Unified Inbox Service."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from app.services.inbox.unified_inbox import UnifiedInboxService
from app.models.responses import CustomerResponse, ResponseStatus, ResponseIntent, ResponseUrgency


class TestUnifiedInboxService:
    """Test Unified Inbox functionality."""

    @pytest.fixture
    def inbox_service(self):
        db = Mock()
        return UnifiedInboxService(db)

    @pytest.fixture
    def mock_messages(self):
        """Create mock customer response messages."""
        messages = []
        for i in range(5):
            msg = Mock(spec=CustomerResponse)
            msg.id = uuid4()
            msg.customer_id = f"customer_{i}"
            msg.customer_name = f"Customer {i}"
            msg.customer_email = f"customer{i}@example.com"
            msg.channel = "email" if i % 2 == 0 else "instagram"
            msg.subject = f"Subject {i}"
            msg.message_body = f"Message body {i}"
            msg.intent = ResponseIntent.QUESTION if i % 2 == 0 else ResponseIntent.PURCHASE_INTENT
            msg.sentiment_score = 0.5
            msg.urgency = ResponseUrgency.MEDIUM
            msg.status = ResponseStatus.NEW
            msg.assigned_to = None
            msg.is_flagged = False
            msg.is_sla_breached = False
            msg.received_at = datetime.utcnow() - timedelta(hours=i)
            msg.first_viewed_at = None
            messages.append(msg)
        return messages

    @pytest.mark.asyncio
    async def test_get_inbox_no_filters(self, inbox_service, mock_messages):
        """Test getting inbox without filters."""
        tenant_uuid = uuid4()

        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = len(mock_messages)
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_messages

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.get_inbox(
            tenant_uuid=tenant_uuid,
            skip=0,
            limit=50,
        )

        assert "messages" in result
        assert result["total"] == len(mock_messages)
        assert len(result["messages"]) == len(mock_messages)
        assert "unread_count" in result
        assert "sla_breach_count" in result

    @pytest.mark.asyncio
    async def test_get_inbox_with_status_filter(self, inbox_service, mock_messages):
        """Test getting inbox with status filter."""
        tenant_uuid = uuid4()

        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_messages[:3]

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.get_inbox(
            tenant_uuid=tenant_uuid,
            filters={"status": ResponseStatus.NEW},
            skip=0,
            limit=50,
        )

        assert result["total"] == 3

    @pytest.mark.asyncio
    async def test_get_inbox_with_channel_filter(self, inbox_service, mock_messages):
        """Test getting inbox with channel filter."""
        tenant_uuid = uuid4()

        email_messages = [m for m in mock_messages if m.channel == "email"]

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = len(email_messages)
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = email_messages

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.get_inbox(
            tenant_uuid=tenant_uuid,
            filters={"channel": "email"},
            skip=0,
            limit=50,
        )

        assert result["total"] == len(email_messages)

    @pytest.mark.asyncio
    async def test_get_inbox_pagination(self, inbox_service, mock_messages):
        """Test inbox pagination."""
        tenant_uuid = uuid4()

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = len(mock_messages)
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_messages[2:4]

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.get_inbox(
            tenant_uuid=tenant_uuid,
            skip=2,
            limit=2,
        )

        assert result["page"] == 2  # (skip 2 / limit 2) + 1
        assert result["total"] == len(mock_messages)

    @pytest.mark.asyncio
    async def test_assign_message_success(self, inbox_service):
        """Test assigning message to team member."""
        response_id = uuid4()
        assigned_to = "agent@example.com"
        team = "support"

        mock_message = Mock(spec=CustomerResponse)
        mock_message.id = response_id
        mock_message.assigned_to = None
        mock_message.assigned_at = None
        mock_message.team = None
        mock_message.status = ResponseStatus.NEW

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_message

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.assign_message(
            response_id=response_id,
            assigned_to=assigned_to,
            team=team,
        )

        assert result["success"] is True
        assert result["assigned_to"] == assigned_to
        assert result["team"] == team
        assert mock_message.status == ResponseStatus.ASSIGNED
        assert mock_message.assigned_to == assigned_to
        inbox_service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_message_not_found(self, inbox_service):
        """Test assigning message that doesn't exist."""
        response_id = uuid4()

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.assign_message(
            response_id=response_id,
            assigned_to="agent@example.com",
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_mark_as_read(self, inbox_service):
        """Test marking message as read."""
        response_id = uuid4()

        mock_message = Mock(spec=CustomerResponse)
        mock_message.id = response_id
        mock_message.first_viewed_at = None

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_message

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.mark_as_read(response_id=response_id)

        assert result["success"] is True
        assert mock_message.first_viewed_at is not None
        inbox_service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_mark_as_read_already_read(self, inbox_service):
        """Test marking message as read when already read."""
        response_id = uuid4()
        original_time = datetime.utcnow() - timedelta(hours=1)

        mock_message = Mock(spec=CustomerResponse)
        mock_message.id = response_id
        mock_message.first_viewed_at = original_time

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_message

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.mark_as_read(response_id=response_id)

        assert result["success"] is True
        # Should not update first_viewed_at if already set
        assert mock_message.first_viewed_at == original_time

    @pytest.mark.asyncio
    async def test_flag_message(self, inbox_service):
        """Test flagging message for review."""
        response_id = uuid4()
        reason = "Inappropriate content"

        mock_message = Mock(spec=CustomerResponse)
        mock_message.id = response_id
        mock_message.is_flagged = False
        mock_message.flag_reason = None

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_message

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.flag_message(
            response_id=response_id,
            reason=reason,
        )

        assert result["success"] is True
        assert result["flagged"] is True
        assert result["reason"] == reason
        assert mock_message.is_flagged is True
        assert mock_message.flag_reason == reason

    @pytest.mark.asyncio
    async def test_get_conversation_thread(self, inbox_service):
        """Test getting conversation thread."""
        conversation_id = uuid4()

        # Create thread of messages
        thread_messages = []
        for i in range(3):
            msg = Mock(spec=CustomerResponse)
            msg.id = uuid4()
            msg.conversation_id = conversation_id
            msg.message_body = f"Message {i}"
            msg.received_at = datetime.utcnow() - timedelta(hours=3-i)
            msg.customer_id = "customer_123"
            msg.customer_name = "Test Customer"
            msg.customer_email = "test@example.com"
            msg.channel = "email"
            msg.subject = "Thread subject"
            msg.intent = None
            msg.sentiment_score = 0.0
            msg.urgency = None
            msg.status = ResponseStatus.NEW
            msg.assigned_to = None
            msg.is_flagged = False
            msg.is_sla_breached = False
            msg.first_viewed_at = None
            thread_messages.append(msg)

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.all.return_value = thread_messages

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.get_conversation_thread(
            conversation_id=conversation_id
        )

        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_get_sla_alerts_breached(self, inbox_service):
        """Test getting SLA alerts for breached messages."""
        tenant_uuid = uuid4()
        now = datetime.utcnow()

        # Create breached message
        breached_msg = Mock(spec=CustomerResponse)
        breached_msg.id = uuid4()
        breached_msg.customer_name = "Customer A"
        breached_msg.sla_breach_at = now - timedelta(hours=2)  # Breached 2 hours ago
        breached_msg.status = ResponseStatus.NEW

        # Create approaching breach message
        approaching_msg = Mock(spec=CustomerResponse)
        approaching_msg.id = uuid4()
        approaching_msg.customer_name = "Customer B"
        approaching_msg.sla_breach_at = now + timedelta(minutes=30)  # 30 min away
        approaching_msg.status = ResponseStatus.ASSIGNED

        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [breached_msg, approaching_msg]

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.get_sla_alerts(tenant_uuid=tenant_uuid)

        assert len(result) == 2
        assert result[0]["status"] == "breached"
        assert result[1]["status"] == "approaching"

    @pytest.mark.asyncio
    async def test_get_inbox_analytics(self, inbox_service, mock_messages):
        """Test getting inbox analytics."""
        tenant_uuid = uuid4()
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()

        # Mock analytics query
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_messages

        inbox_service.db.query.return_value = mock_query

        result = await inbox_service.get_inbox_analytics(
            tenant_uuid=tenant_uuid,
            start_date=start_date,
            end_date=end_date,
        )

        assert "total_messages" in result
        assert "by_channel" in result
        assert "by_intent" in result
        assert "by_urgency" in result
        assert "sla_compliance_rate" in result
        assert "period" in result

        assert result["total_messages"] == len(mock_messages)

    def test_format_message(self, inbox_service):
        """Test message formatting for API response."""
        msg = Mock(spec=CustomerResponse)
        msg.id = uuid4()
        msg.customer_id = "customer_123"
        msg.customer_name = "John Doe"
        msg.customer_email = "john@example.com"
        msg.channel = "email"
        msg.subject = "Test subject"
        msg.message_body = "This is a test message body that is longer than 100 characters so we can test the preview truncation functionality"
        msg.intent = ResponseIntent.QUESTION
        msg.sentiment_score = 0.6
        msg.urgency = ResponseUrgency.HIGH
        msg.status = ResponseStatus.NEW
        msg.assigned_to = None
        msg.is_flagged = False
        msg.is_sla_breached = False
        msg.received_at = datetime.utcnow()
        msg.first_viewed_at = None

        formatted = inbox_service._format_message(msg)

        assert formatted["id"] == str(msg.id)
        assert formatted["customer_email"] == "john@example.com"
        assert formatted["channel"] == "email"
        assert len(formatted["message_preview"]) <= 100
        assert formatted["intent"] == "question"
        assert formatted["urgency"] == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
