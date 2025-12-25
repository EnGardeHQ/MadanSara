"""Unit tests for Walker Agent SDK."""

import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
import httpx

from app.services.integrations.walker_sdk import WalkerAgentSDK


class TestWalkerAgentSDK:
    """Test Walker Agent SDK functionality."""

    @pytest.fixture
    def sdk_with_api_key(self):
        return WalkerAgentSDK(
            api_key="test_api_key",
            base_url="https://test.engarde.com/v1",
        )

    @pytest.fixture
    def sdk_without_api_key(self):
        return WalkerAgentSDK(api_key=None)

    @pytest.mark.asyncio
    async def test_get_tenant_integrations_success(self, sdk_with_api_key):
        """Test getting tenant integrations successfully."""
        tenant_uuid = str(uuid4())

        mock_response = {
            "tenant_uuid": tenant_uuid,
            "integrations": [
                {
                    "id": "email_sendgrid",
                    "name": "SendGrid",
                    "type": "email",
                    "status": "active",
                },
                {
                    "id": "social_meta",
                    "name": "Facebook & Instagram",
                    "type": "social",
                    "status": "active",
                },
            ],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.get_tenant_integrations(
                tenant_uuid=tenant_uuid
            )

            assert "integrations" in result
            assert len(result["integrations"]) == 2
            assert result["integrations"][0]["type"] == "email"

    @pytest.mark.asyncio
    async def test_get_tenant_integrations_filtered(self, sdk_with_api_key):
        """Test getting tenant integrations with type filter."""
        tenant_uuid = str(uuid4())

        mock_response = {
            "tenant_uuid": tenant_uuid,
            "integrations": [
                {
                    "id": "email_sendgrid",
                    "name": "SendGrid",
                    "type": "email",
                    "status": "active",
                },
            ],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.get_tenant_integrations(
                tenant_uuid=tenant_uuid,
                integration_type="email",
            )

            assert len(result["integrations"]) == 1
            assert result["integrations"][0]["type"] == "email"

    @pytest.mark.asyncio
    async def test_get_tenant_integrations_mock_mode(self, sdk_without_api_key):
        """Test getting tenant integrations in mock mode."""
        tenant_uuid = str(uuid4())

        result = await sdk_without_api_key.get_tenant_integrations(
            tenant_uuid=tenant_uuid
        )

        assert result["mock"] is True
        assert "integrations" in result
        assert len(result["integrations"]) > 0

    @pytest.mark.asyncio
    async def test_send_email_via_integration_success(self, sdk_with_api_key):
        """Test sending email through integration."""
        tenant_uuid = str(uuid4())
        integration_id = "email_sendgrid"
        email_data = {
            "to": "customer@example.com",
            "subject": "Test Email",
            "body_html": "<p>Test content</p>",
        }

        mock_response = {
            "success": True,
            "message_id": "msg_123",
            "provider": "sendgrid",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.send_email_via_integration(
                tenant_uuid=tenant_uuid,
                integration_id=integration_id,
                email_data=email_data,
            )

            assert result["success"] is True
            assert "message_id" in result

    @pytest.mark.asyncio
    async def test_send_email_via_integration_failure(self, sdk_with_api_key):
        """Test email send failure."""
        tenant_uuid = str(uuid4())
        integration_id = "email_sendgrid"
        email_data = {"to": "customer@example.com"}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 400
            mock_response_obj.text = "Invalid email data"

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.send_email_via_integration(
                tenant_uuid=tenant_uuid,
                integration_id=integration_id,
                email_data=email_data,
            )

            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_track_website_event_success(self, sdk_with_api_key):
        """Test website event tracking."""
        tenant_uuid = str(uuid4())
        event_data = {
            "event_type": "page_view",
            "visitor_id": "visitor_123",
            "page_url": "https://example.com/product",
        }

        mock_response = {
            "success": True,
            "event_id": "evt_456",
            "routed_to": ["google_analytics", "hubspot"],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.track_website_event(
                tenant_uuid=tenant_uuid,
                event_data=event_data,
            )

            assert result["success"] is True
            assert len(result["routed_to"]) > 0

    @pytest.mark.asyncio
    async def test_track_website_event_mock_mode(self, sdk_without_api_key):
        """Test website event tracking in mock mode."""
        tenant_uuid = str(uuid4())
        event_data = {
            "event_type": "page_view",
            "visitor_id": "visitor_123",
        }

        result = await sdk_without_api_key.track_website_event(
            tenant_uuid=tenant_uuid,
            event_data=event_data,
        )

        assert result["mock"] is True
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_integration_action_success(self, sdk_with_api_key):
        """Test executing generic integration action."""
        tenant_uuid = str(uuid4())
        integration_id = "crm_salesforce"
        action = "create_contact"
        params = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }

        mock_response = {
            "success": True,
            "result": {"contact_id": "sf_123"},
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.execute_integration_action(
                tenant_uuid=tenant_uuid,
                integration_id=integration_id,
                action=action,
                params=params,
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_social_media_accounts_success(self, sdk_with_api_key):
        """Test getting social media accounts."""
        tenant_uuid = str(uuid4())

        mock_response = {
            "accounts": [
                {
                    "id": "fb_123",
                    "platform": "facebook",
                    "name": "Business Page",
                    "status": "connected",
                },
                {
                    "id": "ig_456",
                    "platform": "instagram",
                    "name": "@business",
                    "status": "connected",
                },
            ],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.get_social_media_accounts(
                tenant_uuid=tenant_uuid
            )

            assert len(result) == 2
            assert result[0]["platform"] == "facebook"

    @pytest.mark.asyncio
    async def test_get_social_media_accounts_filtered(self, sdk_with_api_key):
        """Test getting social media accounts with platform filter."""
        tenant_uuid = str(uuid4())

        mock_response = {
            "accounts": [
                {
                    "id": "fb_123",
                    "platform": "facebook",
                    "name": "Business Page",
                },
            ],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.get_social_media_accounts(
                tenant_uuid=tenant_uuid,
                platform="facebook",
            )

            assert len(result) == 1
            assert result[0]["platform"] == "facebook"

    @pytest.mark.asyncio
    async def test_get_crm_contacts_success(self, sdk_with_api_key):
        """Test getting CRM contacts."""
        tenant_uuid = str(uuid4())
        integration_id = "crm_salesforce"

        mock_response = {
            "contacts": [
                {"id": "1", "name": "John Doe", "email": "john@example.com"},
                {"id": "2", "name": "Jane Smith", "email": "jane@example.com"},
            ],
            "total": 2,
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.get_crm_contacts(
                tenant_uuid=tenant_uuid,
                integration_id=integration_id,
                limit=100,
            )

            assert result["total"] == 2
            assert len(result["contacts"]) == 2

    @pytest.mark.asyncio
    async def test_sync_conversion_to_crm_success(self, sdk_with_api_key):
        """Test syncing conversion to CRM."""
        tenant_uuid = str(uuid4())
        integration_id = "crm_salesforce"
        conversion_data = {
            "conversion_id": "conv_123",
            "customer_id": "cust_456",
            "conversion_type": "purchase",
            "conversion_value": 99.99,
        }

        mock_response = {
            "success": True,
            "crm_record_id": "sf_record_789",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.sync_conversion_to_crm(
                tenant_uuid=tenant_uuid,
                integration_id=integration_id,
                conversion_data=conversion_data,
            )

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_get_analytics_data_success(self, sdk_with_api_key):
        """Test getting analytics data."""
        tenant_uuid = str(uuid4())
        integration_id = "tracking_ga4"
        metrics = ["page_views", "sessions", "conversions"]

        mock_response = {
            "data": [
                {"metric": "page_views", "value": 1500},
                {"metric": "sessions", "value": 800},
                {"metric": "conversions", "value": 45},
            ],
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_response_obj = Mock()
            mock_response_obj.status_code = 200
            mock_response_obj.json.return_value = mock_response

            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response_obj
            )

            result = await sdk_with_api_key.get_analytics_data(
                tenant_uuid=tenant_uuid,
                integration_id=integration_id,
                metrics=metrics,
                start_date="2024-01-01",
                end_date="2024-01-31",
            )

            assert len(result["data"]) == 3
            assert result["data"][0]["metric"] == "page_views"

    @pytest.mark.asyncio
    async def test_api_error_handling(self, sdk_with_api_key):
        """Test API error handling."""
        tenant_uuid = str(uuid4())

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=Exception("Network error")
            )

            result = await sdk_with_api_key.get_tenant_integrations(
                tenant_uuid=tenant_uuid
            )

            assert "error" in result
            assert "Network error" in result["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
