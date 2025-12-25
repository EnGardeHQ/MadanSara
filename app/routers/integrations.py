"""Integration management API endpoints - Walker Agent SDK."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Any, Optional
from uuid import UUID

from app.services.integrations.walker_sdk import WalkerAgentSDK

router = APIRouter()


@router.get("/tenants/{tenant_uuid}/integrations")
async def get_tenant_integrations(
    tenant_uuid: UUID,
    integration_type: Optional[str] = None,
):
    """
    Get all integrations configured for a tenant.

    Query params:
        integration_type: Filter by type (email, social, analytics, crm)
    """
    sdk = WalkerAgentSDK()
    result = await sdk.get_tenant_integrations(
        tenant_uuid=str(tenant_uuid),
        integration_type=integration_type,
    )
    return result


@router.post("/integrations/{integration_id}/email/send")
async def send_email_via_integration(
    integration_id: str,
    data: Dict[str, Any],
):
    """
    Send email through tenant's configured email integration.

    Body:
        tenant_uuid: Tenant UUID
        to: Recipient email
        subject: Email subject
        body_html: HTML body
        body_text: Plain text body (optional)
        from_name: Sender name (optional)
        reply_to: Reply-to address (optional)
        personalization_data: Personalization variables (optional)
    """
    tenant_uuid = data.get("tenant_uuid")
    if not tenant_uuid:
        raise HTTPException(status_code=400, detail="tenant_uuid required")

    sdk = WalkerAgentSDK()
    result = await sdk.send_email_via_integration(
        tenant_uuid=tenant_uuid,
        integration_id=integration_id,
        email_data=data,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.post("/tenants/{tenant_uuid}/tracking/event")
async def track_website_event(
    tenant_uuid: UUID,
    event_data: Dict[str, Any],
):
    """
    Send website tracking event to tenant's configured tracking platforms.

    Automatically routes to WordPress, HubSpot, Google Analytics, Intuit, etc.

    Body:
        event_type: Event type (page_view, click, form_submit, etc.)
        visitor_id: Visitor ID
        session_id: Session ID
        page_url: Current page URL
        event_data: Additional event data
    """
    sdk = WalkerAgentSDK()
    result = await sdk.track_website_event(
        tenant_uuid=str(tenant_uuid),
        event_data=event_data,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/integrations/{integration_id}/credentials")
async def get_integration_credentials(
    integration_id: str,
    tenant_uuid: UUID,
):
    """Get credentials for a specific integration (masked for security)."""
    sdk = WalkerAgentSDK()
    result = await sdk.get_integration_credentials(
        tenant_uuid=str(tenant_uuid),
        integration_id=integration_id,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.post("/integrations/{integration_id}/execute")
async def execute_integration_action(
    integration_id: str,
    data: Dict[str, Any],
):
    """
    Execute a generic action through an integration.

    Body:
        tenant_uuid: Tenant UUID
        action: Action name (send_email, post_social, create_contact, etc.)
        params: Action parameters
    """
    tenant_uuid = data.get("tenant_uuid")
    action = data.get("action")
    params = data.get("params", {})

    if not tenant_uuid or not action:
        raise HTTPException(status_code=400, detail="tenant_uuid and action required")

    sdk = WalkerAgentSDK()
    result = await sdk.execute_integration_action(
        tenant_uuid=tenant_uuid,
        integration_id=integration_id,
        action=action,
        params=params,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.get("/tenants/{tenant_uuid}/social-accounts")
async def get_social_media_accounts(
    tenant_uuid: UUID,
    platform: Optional[str] = None,
):
    """
    Get connected social media accounts for tenant.

    Query params:
        platform: Filter by platform (facebook, instagram, linkedin, twitter)
    """
    sdk = WalkerAgentSDK()
    accounts = await sdk.get_social_media_accounts(
        tenant_uuid=str(tenant_uuid),
        platform=platform,
    )
    return {"accounts": accounts}


@router.get("/integrations/{integration_id}/crm/contacts")
async def get_crm_contacts(
    integration_id: str,
    tenant_uuid: UUID,
    limit: int = 100,
):
    """Get contacts from CRM integration."""
    sdk = WalkerAgentSDK()
    result = await sdk.get_crm_contacts(
        tenant_uuid=str(tenant_uuid),
        integration_id=integration_id,
        limit=limit,
    )
    return result


@router.post("/integrations/{integration_id}/crm/sync-conversion")
async def sync_conversion_to_crm(
    integration_id: str,
    conversion_data: Dict[str, Any],
):
    """
    Sync conversion event to CRM.

    Body:
        tenant_uuid: Tenant UUID
        conversion_id: Conversion event ID
        customer_id: Customer ID
        conversion_type: Conversion type
        conversion_value: Conversion value
        ...additional conversion data
    """
    tenant_uuid = conversion_data.get("tenant_uuid")
    if not tenant_uuid:
        raise HTTPException(status_code=400, detail="tenant_uuid required")

    sdk = WalkerAgentSDK()
    result = await sdk.sync_conversion_to_crm(
        tenant_uuid=tenant_uuid,
        integration_id=integration_id,
        conversion_data=conversion_data,
    )

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.post("/integrations/{integration_id}/analytics/query")
async def get_analytics_data(
    integration_id: str,
    query_data: Dict[str, Any],
):
    """
    Get analytics data from integration.

    Body:
        tenant_uuid: Tenant UUID
        metrics: List of metrics to retrieve
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    """
    tenant_uuid = query_data.get("tenant_uuid")
    metrics = query_data.get("metrics", [])
    start_date = query_data.get("start_date")
    end_date = query_data.get("end_date")

    if not all([tenant_uuid, metrics, start_date, end_date]):
        raise HTTPException(
            status_code=400,
            detail="tenant_uuid, metrics, start_date, and end_date required",
        )

    sdk = WalkerAgentSDK()
    result = await sdk.get_analytics_data(
        tenant_uuid=tenant_uuid,
        integration_id=integration_id,
        metrics=metrics,
        start_date=start_date,
        end_date=end_date,
    )

    return result
