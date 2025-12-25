"""Outreach campaign and message management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.models.outreach import OutreachCampaign, OutreachMessage
from app.services.orchestrator import OutreachOrchestrator

router = APIRouter()


@router.get("/campaigns")
async def list_campaigns(
    tenant_uuid: UUID,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all outreach campaigns for a tenant."""
    # campaigns = db.query(OutreachCampaign).filter(
    #     OutreachCampaign.tenant_uuid == tenant_uuid
    # ).offset(skip).limit(limit).all()
    return {"campaigns": [], "total": 0}


@router.post("/campaigns")
async def create_campaign(
    campaign_data: dict,
    db: Session = Depends(get_db),
):
    """Create a new outreach campaign."""
    # Implementation here
    return {"message": "Campaign creation endpoint", "data": campaign_data}


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: UUID,
    db: Session = Depends(get_db),
):
    """Get campaign details."""
    # campaign = db.query(OutreachCampaign).filter(
    #     OutreachCampaign.id == campaign_id
    # ).first()
    # if not campaign:
    #     raise HTTPException(status_code=404, detail="Campaign not found")
    return {"campaign_id": str(campaign_id)}


@router.post("/send")
async def send_outreach(
    outreach_data: dict,
    db: Session = Depends(get_db),
):
    """
    Send multi-channel outreach message using intelligent orchestration.

    Request body should include:
    - campaign_id: UUID of the campaign
    - recipient_id: Unique recipient identifier
    - recipient_profile: Dict with contact info, preferences, customer_type
    - content: Dict with message content per channel

    Example:
    {
        "campaign_id": "...",
        "recipient_id": "user123",
        "recipient_profile": {
            "name": "John Doe",
            "customer_type": "new",
            "contact_info": {
                "email": "john@example.com",
                "instagram_handle": "@johndoe"
            },
            "preferences": {
                "preferred_channel": "email"
            }
        },
        "content": {
            "email": "Hello {{name}}, check out our offer!",
            "instagram": "Hey {{name}}! 👋 Special offer just for you!"
        }
    }
    """
    # Get campaign
    campaign_id = outreach_data.get("campaign_id")
    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id required")

    campaign = db.query(OutreachCampaign).filter(
        OutreachCampaign.id == campaign_id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Initialize orchestrator
    orchestrator = OutreachOrchestrator(db)

    # Send via orchestrator
    result = await orchestrator.send_outreach(
        campaign=campaign,
        recipient_id=outreach_data.get("recipient_id"),
        recipient_profile=outreach_data.get("recipient_profile", {}),
        content=outreach_data.get("content", {}),
        force_send=outreach_data.get("force_send", False),
    )

    return result


@router.get("/messages")
async def list_messages(
    tenant_uuid: UUID,
    campaign_id: UUID = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List outreach messages."""
    return {"messages": [], "total": 0}


@router.get("/messages/{message_id}")
async def get_message(
    message_id: UUID,
    db: Session = Depends(get_db),
):
    """Get message details and status."""
    return {"message_id": str(message_id)}


@router.post("/templates")
async def create_template(
    template_data: dict,
    db: Session = Depends(get_db),
):
    """Create a channel template."""
    return {"message": "Template creation endpoint", "data": template_data}


@router.get("/templates")
async def list_templates(
    tenant_uuid: UUID,
    channel: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List available templates."""
    return {"templates": [], "total": 0}


@router.post("/send-batch")
async def send_batch_outreach(
    batch_data: dict,
    db: Session = Depends(get_db),
):
    """
    Send outreach to multiple recipients using intelligent orchestration.

    Handles batching, pacing, and per-recipient optimization.
    """
    campaign_id = batch_data.get("campaign_id")
    if not campaign_id:
        raise HTTPException(status_code=400, detail="campaign_id required")

    campaign = db.query(OutreachCampaign).filter(
        OutreachCampaign.id == campaign_id
    ).first()

    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    orchestrator = OutreachOrchestrator(db)

    result = await orchestrator.send_batch(
        campaign=campaign,
        recipients=batch_data.get("recipients", []),
        content_templates=batch_data.get("content", {}),
    )

    return result


@router.get("/campaigns/{campaign_id}/status")
async def get_orchestration_status(
    campaign_id: UUID,
    db: Session = Depends(get_db),
):
    """Get current orchestration status for a campaign."""
    orchestrator = OutreachOrchestrator(db)
    status = await orchestrator.get_orchestration_status(campaign_id)
    return status
