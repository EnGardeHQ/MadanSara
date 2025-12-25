"""Walker Agent SDK - Client for En Garde platform integrations."""

from typing import Dict, List, Optional, Any
import os
import httpx
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class WalkerAgentSDK:
    """
    Client for interacting with En Garde platform integrations.

    Provides access to third-party integrations configured in En Garde:
    - Email marketing platforms (SendGrid, Mailchimp, AWS SES, etc.)
    - Website tracking (WordPress, HubSpot, Google Analytics, Intuit, etc.)
    - Social media platforms (Facebook, Instagram, LinkedIn, Twitter)
    - CRM systems (Salesforce, HubSpot, Pipedrive, etc.)
    - Analytics platforms (Google Analytics, Mixpanel, Amplitude, etc.)
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("ENGARDE_API_KEY")
        self.base_url = base_url or os.getenv("ENGARDE_BASE_URL", "https://api.engarde.com/v1")

        if not self.api_key:
            logger.warning("ENGARDE_API_KEY not configured - Walker SDK will operate in mock mode")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "MadanSara/1.0",
        }

    async def get_tenant_integrations(
        self,
        tenant_uuid: str,
        integration_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get all integrations configured for a tenant.

        Args:
            tenant_uuid: Tenant UUID
            integration_type: Optional filter (email, social, analytics, crm, etc.)

        Returns:
            List of configured integrations
        """
        if not self.api_key:
            return self._mock_integrations(tenant_uuid, integration_type)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/tenants/{tenant_uuid}/integrations"
                params = {}
                if integration_type:
                    params["type"] = integration_type

                response = await client.get(url, headers=self.headers, params=params)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to fetch integrations: {response.status_code} {response.text}")
                    return {"error": response.text, "integrations": []}

        except Exception as e:
            logger.error(f"Error fetching integrations: {str(e)}")
            return {"error": str(e), "integrations": []}

    async def send_email_via_integration(
        self,
        tenant_uuid: str,
        integration_id: str,
        email_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send email through tenant's configured email integration.

        Args:
            tenant_uuid: Tenant UUID
            integration_id: Integration ID (or "auto" to use default)
            email_data: Email data (to, subject, body, etc.)

        Returns:
            Send result
        """
        if not self.api_key:
            return self._mock_email_send(email_data)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/integrations/{integration_id}/email/send"

                payload = {
                    "tenant_uuid": tenant_uuid,
                    **email_data,
                }

                response = await client.post(url, headers=self.headers, json=payload)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def track_website_event(
        self,
        tenant_uuid: str,
        event_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Send website tracking event to tenant's configured tracking platforms.

        Automatically routes to WordPress, HubSpot, Google Analytics, Intuit, etc.
        based on tenant's integration configuration.

        Args:
            tenant_uuid: Tenant UUID
            event_data: Event data (event_type, visitor_id, page_url, etc.)

        Returns:
            Tracking result
        """
        if not self.api_key:
            return self._mock_tracking_event(event_data)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/tenants/{tenant_uuid}/tracking/event"

                payload = {
                    "tenant_uuid": tenant_uuid,
                    **event_data,
                }

                response = await client.post(url, headers=self.headers, json=payload)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": response.text,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_integration_credentials(
        self,
        tenant_uuid: str,
        integration_id: str,
    ) -> Dict[str, Any]:
        """
        Get credentials for a specific integration.

        Args:
            tenant_uuid: Tenant UUID
            integration_id: Integration ID

        Returns:
            Integration credentials (masked for security)
        """
        if not self.api_key:
            return {"error": "Not configured"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/integrations/{integration_id}/credentials"
                params = {"tenant_uuid": tenant_uuid}

                response = await client.get(url, headers=self.headers, params=params)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.text}

        except Exception as e:
            return {"error": str(e)}

    async def execute_integration_action(
        self,
        tenant_uuid: str,
        integration_id: str,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a generic action through an integration.

        Args:
            tenant_uuid: Tenant UUID
            integration_id: Integration ID
            action: Action name (send_email, post_social, create_contact, etc.)
            params: Action parameters

        Returns:
            Action result
        """
        if not self.api_key:
            return self._mock_action_execution(action, params)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/integrations/{integration_id}/execute"

                payload = {
                    "tenant_uuid": tenant_uuid,
                    "action": action,
                    "params": params,
                }

                response = await client.post(url, headers=self.headers, json=payload)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {
                        "success": False,
                        "error": response.text,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_social_media_accounts(
        self,
        tenant_uuid: str,
        platform: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get connected social media accounts for tenant.

        Args:
            tenant_uuid: Tenant UUID
            platform: Optional platform filter (facebook, instagram, linkedin, twitter)

        Returns:
            List of connected accounts
        """
        if not self.api_key:
            return self._mock_social_accounts(platform)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/tenants/{tenant_uuid}/social-accounts"
                params = {}
                if platform:
                    params["platform"] = platform

                response = await client.get(url, headers=self.headers, params=params)

                if response.status_code == 200:
                    result = response.json()
                    return result.get("accounts", [])
                else:
                    return []

        except Exception as e:
            logger.error(f"Error fetching social accounts: {str(e)}")
            return []

    async def get_crm_contacts(
        self,
        tenant_uuid: str,
        integration_id: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get contacts from CRM integration.

        Args:
            tenant_uuid: Tenant UUID
            integration_id: CRM integration ID
            filters: Optional filters
            limit: Max results

        Returns:
            CRM contacts
        """
        if not self.api_key:
            return {"contacts": [], "total": 0}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/integrations/{integration_id}/crm/contacts"

                params = {
                    "tenant_uuid": tenant_uuid,
                    "limit": limit,
                }
                if filters:
                    params["filters"] = filters

                response = await client.get(url, headers=self.headers, params=params)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"contacts": [], "error": response.text}

        except Exception as e:
            return {"contacts": [], "error": str(e)}

    async def sync_conversion_to_crm(
        self,
        tenant_uuid: str,
        integration_id: str,
        conversion_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sync conversion event to CRM.

        Args:
            tenant_uuid: Tenant UUID
            integration_id: CRM integration ID
            conversion_data: Conversion event data

        Returns:
            Sync result
        """
        if not self.api_key:
            return {"success": True, "mock": True}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/integrations/{integration_id}/crm/sync-conversion"

                payload = {
                    "tenant_uuid": tenant_uuid,
                    **conversion_data,
                }

                response = await client.post(url, headers=self.headers, json=payload)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"success": False, "error": response.text}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_analytics_data(
        self,
        tenant_uuid: str,
        integration_id: str,
        metrics: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, Any]:
        """
        Get analytics data from integration.

        Args:
            tenant_uuid: Tenant UUID
            integration_id: Analytics integration ID
            metrics: Metrics to retrieve
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            Analytics data
        """
        if not self.api_key:
            return {"data": [], "mock": True}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/integrations/{integration_id}/analytics/query"

                payload = {
                    "tenant_uuid": tenant_uuid,
                    "metrics": metrics,
                    "start_date": start_date,
                    "end_date": end_date,
                }

                response = await client.post(url, headers=self.headers, json=payload)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"data": [], "error": response.text}

        except Exception as e:
            return {"data": [], "error": str(e)}

    # Mock methods for development/testing

    def _mock_integrations(
        self,
        tenant_uuid: str,
        integration_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mock integrations for development."""
        all_integrations = [
            {
                "id": "email_sendgrid",
                "name": "SendGrid",
                "type": "email",
                "status": "active",
                "provider": "sendgrid",
            },
            {
                "id": "email_mailchimp",
                "name": "Mailchimp",
                "type": "email",
                "status": "active",
                "provider": "mailchimp",
            },
            {
                "id": "social_meta",
                "name": "Facebook & Instagram",
                "type": "social",
                "status": "active",
                "provider": "meta",
            },
            {
                "id": "tracking_ga4",
                "name": "Google Analytics 4",
                "type": "analytics",
                "status": "active",
                "provider": "google_analytics",
            },
            {
                "id": "tracking_hubspot",
                "name": "HubSpot",
                "type": "analytics",
                "status": "active",
                "provider": "hubspot",
            },
            {
                "id": "crm_salesforce",
                "name": "Salesforce",
                "type": "crm",
                "status": "active",
                "provider": "salesforce",
            },
        ]

        if integration_type:
            integrations = [i for i in all_integrations if i["type"] == integration_type]
        else:
            integrations = all_integrations

        return {
            "tenant_uuid": tenant_uuid,
            "integrations": integrations,
            "mock": True,
        }

    def _mock_email_send(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock email send for development."""
        return {
            "success": True,
            "message_id": f"mock_{datetime.utcnow().timestamp()}",
            "provider": "mock",
            "mock": True,
        }

    def _mock_tracking_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tracking event for development."""
        return {
            "success": True,
            "event_id": f"evt_{datetime.utcnow().timestamp()}",
            "routed_to": ["google_analytics", "hubspot"],
            "mock": True,
        }

    def _mock_action_execution(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mock action execution for development."""
        return {
            "success": True,
            "action": action,
            "result": "Action executed successfully",
            "mock": True,
        }

    def _mock_social_accounts(
        self,
        platform: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Mock social accounts for development."""
        accounts = [
            {
                "id": "fb_123",
                "platform": "facebook",
                "name": "Business Page",
                "status": "connected",
            },
            {
                "id": "ig_456",
                "platform": "instagram",
                "name": "@businesshandle",
                "status": "connected",
            },
            {
                "id": "tw_789",
                "platform": "twitter",
                "name": "@businesstwitter",
                "status": "connected",
            },
        ]

        if platform:
            return [a for a in accounts if a["platform"] == platform]
        return accounts
