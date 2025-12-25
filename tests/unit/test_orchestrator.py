"""Unit tests for Outreach Orchestrator."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from app.services.orchestrator.orchestrator import OutreachOrchestrator
from app.services.orchestrator.channel_selector import ChannelSelector
from app.services.orchestrator.deduplicator import MessageDeduplicator
from app.services.orchestrator.budget_manager import BudgetManager
from app.models.outreach import OutreachCampaign


class TestChannelSelector:
    """Test channel selection logic."""

    @pytest.fixture
    def selector(self):
        db = Mock()
        return ChannelSelector(db)

    @pytest.mark.asyncio
    async def test_select_channel_for_mobile_user(self, selector):
        """Test channel selection for mobile user."""
        recipient_profile = {
            "customer_type": "new",
            "device": "mobile",
            "timezone": "America/New_York",
            "engagement_history": {
                "email": {"open_rate": 0.3, "click_rate": 0.1},
                "instagram": {"engagement_rate": 0.6},
            },
        }

        campaign_context = {
            "available_channels": ["email", "instagram", "facebook"],
            "urgency": "medium",
        }

        channel = await selector.select_channel(
            recipient_profile=recipient_profile,
            campaign_context=campaign_context,
        )

        # Mobile users should prefer instagram over email
        assert channel in ["instagram", "facebook"]

    @pytest.mark.asyncio
    async def test_select_channel_for_desktop_user(self, selector):
        """Test channel selection for desktop user."""
        recipient_profile = {
            "customer_type": "returning",
            "device": "desktop",
            "timezone": "America/New_York",
            "engagement_history": {
                "email": {"open_rate": 0.7, "click_rate": 0.3},
                "instagram": {"engagement_rate": 0.2},
            },
        }

        campaign_context = {
            "available_channels": ["email", "instagram"],
            "urgency": "low",
        }

        channel = await selector.select_channel(
            recipient_profile=recipient_profile,
            campaign_context=campaign_context,
        )

        # Desktop users with high email engagement should get email
        assert channel == "email"

    @pytest.mark.asyncio
    async def test_channel_scoring_weights(self, selector):
        """Test that channel scoring uses proper weights."""
        channel = "email"
        customer_type = "returning"
        engagement_history = {
            "email": {"open_rate": 0.5, "click_rate": 0.2}
        }

        score = await selector._calculate_channel_score(
            channel=channel,
            recipient_profile={
                "customer_type": customer_type,
                "device": "desktop",
                "urgency": "medium",
                "engagement_history": engagement_history,
            },
            campaign_context={},
        )

        # Score should be between 0 and 1
        assert 0 <= score <= 1


class TestMessageDeduplicator:
    """Test message deduplication logic."""

    @pytest.fixture
    def deduplicator(self):
        db = Mock()
        return MessageDeduplicator(db)

    @pytest.mark.asyncio
    async def test_check_duplicate_no_previous_send(self, deduplicator):
        """Test deduplication when no previous send exists."""
        tenant_uuid = uuid4()
        recipient_id = "customer_123"
        message_hash = "content_hash_abc"

        # Mock query to return no results
        deduplicator.db.query.return_value.filter.return_value.filter.return_value.first.return_value = None

        result = await deduplicator.check_duplicate(
            tenant_uuid=tenant_uuid,
            recipient_id=recipient_id,
            message_hash=message_hash,
        )

        assert result["is_duplicate"] is False
        assert result["can_send"] is True

    @pytest.mark.asyncio
    async def test_check_duplicate_recent_send(self, deduplicator):
        """Test deduplication when recent send exists."""
        tenant_uuid = uuid4()
        recipient_id = "customer_123"
        message_hash = "content_hash_abc"

        # Mock query to return a recent message
        mock_message = Mock()
        mock_message.sent_at = datetime.utcnow() - timedelta(hours=12)
        deduplicator.db.query.return_value.filter.return_value.filter.return_value.first.return_value = mock_message

        result = await deduplicator.check_duplicate(
            tenant_uuid=tenant_uuid,
            recipient_id=recipient_id,
            message_hash=message_hash,
        )

        assert result["is_duplicate"] is True
        assert result["can_send"] is False

    @pytest.mark.asyncio
    async def test_frequency_cap_within_limits(self, deduplicator):
        """Test frequency cap when within limits."""
        tenant_uuid = uuid4()
        recipient_id = "customer_123"

        # Mock query to return 2 messages in last 24 hours
        deduplicator.db.query.return_value.filter.return_value.count.side_effect = [2, 5]

        result = await deduplicator.apply_frequency_cap(
            tenant_uuid=tenant_uuid,
            recipient_id=recipient_id,
            max_messages_per_day=3,
            max_messages_per_week=10,
        )

        assert result["can_send"] is True
        assert result["daily_count"] == 2
        assert result["weekly_count"] == 5

    @pytest.mark.asyncio
    async def test_frequency_cap_exceeded_daily(self, deduplicator):
        """Test frequency cap when daily limit exceeded."""
        tenant_uuid = uuid4()
        recipient_id = "customer_123"

        # Mock query to return 3 messages in last 24 hours (at limit)
        deduplicator.db.query.return_value.filter.return_value.count.side_effect = [3, 5]

        result = await deduplicator.apply_frequency_cap(
            tenant_uuid=tenant_uuid,
            recipient_id=recipient_id,
            max_messages_per_day=3,
            max_messages_per_week=10,
        )

        assert result["can_send"] is False
        assert result["reason"] == "daily_limit_reached"


class TestBudgetManager:
    """Test budget management logic."""

    @pytest.fixture
    def budget_manager(self):
        db = Mock()
        return BudgetManager(db)

    @pytest.mark.asyncio
    async def test_check_budget_available(self, budget_manager):
        """Test budget availability check."""
        campaign_id = uuid4()
        channel = "email"
        cost = 0.50

        # Mock campaign with budget
        mock_campaign = Mock()
        mock_campaign.total_budget = 1000.0
        mock_campaign.budget_per_channel = {"email": 300.0}
        budget_manager.db.query.return_value.filter.return_value.first.return_value = mock_campaign

        # Mock spent amounts
        budget_manager.db.query.return_value.filter.return_value.filter.return_value.scalar.side_effect = [
            100.0,  # total spent
            30.0,  # channel spent
        ]

        result = await budget_manager.check_budget_available(
            campaign_id=campaign_id,
            channel=channel,
            cost=cost,
        )

        assert result["available"] is True
        assert result["total_remaining"] == 900.0
        assert result["channel_remaining"] == 270.0

    @pytest.mark.asyncio
    async def test_budget_exceeded(self, budget_manager):
        """Test when budget is exceeded."""
        campaign_id = uuid4()
        channel = "email"
        cost = 0.50

        # Mock campaign with budget
        mock_campaign = Mock()
        mock_campaign.total_budget = 1000.0
        mock_campaign.budget_per_channel = {"email": 300.0}
        budget_manager.db.query.return_value.filter.return_value.first.return_value = mock_campaign

        # Mock spent amounts - channel budget nearly exhausted
        budget_manager.db.query.return_value.filter.return_value.filter.return_value.scalar.side_effect = [
            500.0,  # total spent
            299.60,  # channel spent
        ]

        result = await budget_manager.check_budget_available(
            campaign_id=campaign_id,
            channel=channel,
            cost=cost,
        )

        assert result["available"] is False
        assert result["reason"] == "channel_budget_exceeded"

    @pytest.mark.asyncio
    async def test_budget_pacing_on_track(self, budget_manager):
        """Test budget pacing when on track."""
        campaign_id = uuid4()

        # Mock campaign
        mock_campaign = Mock()
        mock_campaign.total_budget = 1000.0
        mock_campaign.start_date = datetime.utcnow() - timedelta(days=5)
        mock_campaign.end_date = datetime.utcnow() + timedelta(days=5)
        budget_manager.db.query.return_value.filter.return_value.first.return_value = mock_campaign

        # Mock spent: $500 spent in 5 days (should be on track for 10-day campaign)
        budget_manager.db.query.return_value.filter.return_value.filter.return_value.scalar.return_value = 500.0

        result = await budget_manager.get_budget_pacing_recommendation(
            campaign_id=campaign_id
        )

        assert result["pacing_status"] == "on_track"
        assert abs(result["actual_daily_spend"] - 100.0) < 1.0  # $500 / 5 days


class TestOutreachOrchestrator:
    """Test orchestrator coordination."""

    @pytest.fixture
    def orchestrator(self):
        db = Mock()
        return OutreachOrchestrator(db)

    @pytest.fixture
    def mock_campaign(self):
        campaign = Mock(spec=OutreachCampaign)
        campaign.id = uuid4()
        campaign.channels = ["email", "instagram"]
        campaign.channel_priority = ["email", "instagram"]
        campaign.total_budget = 1000.0
        campaign.budget_per_channel = {"email": 500.0, "instagram": 500.0}
        campaign.messages_per_day = 3
        campaign.messages_per_week = 10
        return campaign

    @pytest.mark.asyncio
    async def test_send_outreach_success(self, orchestrator, mock_campaign):
        """Test successful outreach send."""
        recipient_id = "customer_123"
        recipient_profile = {
            "customer_type": "new",
            "device": "mobile",
            "timezone": "America/New_York",
            "engagement_history": {},
        }
        content = {
            "email": "Test email content",
            "instagram": "Test IG content",
        }

        # Mock deduplication check
        with patch.object(orchestrator.deduplicator, "check_duplicate", new_callable=AsyncMock) as mock_dedup:
            mock_dedup.return_value = {"is_duplicate": False, "can_send": True}

            # Mock frequency cap
            with patch.object(orchestrator.deduplicator, "apply_frequency_cap", new_callable=AsyncMock) as mock_freq:
                mock_freq.return_value = {"can_send": True}

                # Mock channel selection
                with patch.object(orchestrator.channel_selector, "select_channel", new_callable=AsyncMock) as mock_select:
                    mock_select.return_value = "email"

                    # Mock budget check
                    with patch.object(orchestrator.budget_manager, "check_budget_available", new_callable=AsyncMock) as mock_budget:
                        mock_budget.return_value = {"available": True}

                        # Mock scheduler
                        with patch.object(orchestrator.scheduler, "get_optimal_send_time", new_callable=AsyncMock) as mock_schedule:
                            mock_schedule.return_value = datetime.utcnow()

                            result = await orchestrator.send_outreach(
                                campaign=mock_campaign,
                                recipient_id=recipient_id,
                                recipient_profile=recipient_profile,
                                content=content,
                            )

                            assert result["success"] is True
                            assert result["channel"] == "email"

    @pytest.mark.asyncio
    async def test_send_outreach_duplicate_blocked(self, orchestrator, mock_campaign):
        """Test outreach blocked by deduplication."""
        recipient_id = "customer_123"
        recipient_profile = {"customer_type": "new"}
        content = {"email": "Test content"}

        # Mock deduplication to block send
        with patch.object(orchestrator.deduplicator, "check_duplicate", new_callable=AsyncMock) as mock_dedup:
            mock_dedup.return_value = {
                "is_duplicate": True,
                "can_send": False,
                "reason": "duplicate_content",
            }

            result = await orchestrator.send_outreach(
                campaign=mock_campaign,
                recipient_id=recipient_id,
                recipient_profile=recipient_profile,
                content=content,
            )

            assert result["success"] is False
            assert result["reason"] == "duplicate_content"

    @pytest.mark.asyncio
    async def test_send_batch_outreach(self, orchestrator, mock_campaign):
        """Test batch outreach sending."""
        recipients = [
            {
                "recipient_id": "customer_1",
                "recipient_profile": {"customer_type": "new"},
                "content": {"email": "Content 1"},
            },
            {
                "recipient_id": "customer_2",
                "recipient_profile": {"customer_type": "returning"},
                "content": {"email": "Content 2"},
            },
        ]

        # Mock all checks to pass
        with patch.object(orchestrator, "send_outreach", new_callable=AsyncMock) as mock_send:
            mock_send.side_effect = [
                {"success": True, "channel": "email", "message_id": "msg_1"},
                {"success": True, "channel": "email", "message_id": "msg_2"},
            ]

            result = await orchestrator.send_batch(
                campaign=mock_campaign,
                recipients=recipients,
            )

            assert result["total"] == 2
            assert result["successful"] == 2
            assert result["failed"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
