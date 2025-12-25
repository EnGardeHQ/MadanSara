"""Response management and unified inbox API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.core.database import get_db
from app.services.inbox.unified_inbox import UnifiedInboxService
from app.services.ai_classification.classifier import AIResponseClassifier
from app.models.responses import CustomerResponse

router = APIRouter()


@router.get("/inbox")
async def get_inbox(
    tenant_uuid: UUID,
    status: str = None,
    assigned_to: str = None,
    channel: str = None,
    intent: str = None,
    urgency: str = None,
    is_flagged: bool = None,
    sla_breached: bool = None,
    sort_by: str = "received_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Get unified inbox messages with filtering and pagination."""
    inbox_service = UnifiedInboxService(db)

    # Build filters
    filters = {}
    if status:
        filters["status"] = status
    if assigned_to:
        filters["assigned_to"] = assigned_to
    if channel:
        filters["channel"] = channel
    if intent:
        filters["intent"] = intent
    if urgency:
        filters["urgency"] = urgency
    if is_flagged is not None:
        filters["is_flagged"] = is_flagged
    if sla_breached is not None:
        filters["sla_breached"] = sla_breached

    result = await inbox_service.get_inbox(
        tenant_uuid=tenant_uuid,
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )

    return result


@router.get("/inbox/{response_id}")
async def get_response(
    response_id: UUID,
    db: Session = Depends(get_db),
):
    """Get response details."""
    return {"response_id": str(response_id)}


@router.post("/inbox/{response_id}/assign")
async def assign_response(
    response_id: UUID,
    assigned_to: str,
    team: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Assign response to team member."""
    inbox_service = UnifiedInboxService(db)

    result = await inbox_service.assign_message(
        response_id=response_id,
        assigned_to=assigned_to,
        team=team,
    )

    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error"))

    return result


@router.post("/inbox/{response_id}/reply")
async def send_reply(
    response_id: UUID,
    reply_data: dict,
    db: Session = Depends(get_db),
):
    """Send reply to customer response."""
    return {"message": "Reply sent", "response_id": str(response_id)}


@router.get("/conversations")
async def list_conversations(
    tenant_uuid: UUID,
    customer_id: str = None,
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List conversations."""
    return {"conversations": [], "total": 0}


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
):
    """Get conversation thread."""
    return {"conversation_id": str(conversation_id), "messages": []}


@router.post("/classify")
async def classify_response(
    response_id: UUID,
    db: Session = Depends(get_db),
):
    """Trigger AI classification of response."""
    # Get the response from database
    response = db.query(CustomerResponse).filter(
        CustomerResponse.id == response_id
    ).first()

    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    # Classify with AI
    classifier = AIResponseClassifier()

    classification = await classifier.classify_response(
        message_text=response.message_body,
        channel=response.channel,
        customer_history={
            "customer_id": response.customer_id,
            "customer_name": response.customer_name,
            "customer_email": response.customer_email,
        },
    )

    if "error" in classification:
        raise HTTPException(status_code=500, detail=classification["error"])

    # Update response with classification
    response.intent = classification.get("intent")
    response.sentiment_score = classification.get("sentiment", {}).get("score", 0.0)
    response.urgency = classification.get("urgency", {}).get("level", "medium")

    # Store full classification in extra_data
    if not response.extra_data:
        response.extra_data = {}
    response.extra_data["ai_classification"] = classification

    db.commit()

    return {
        "response_id": str(response_id),
        "classification": classification,
    }


@router.post("/classify/batch")
async def classify_batch_responses(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Classify multiple responses in batch."""
    response_ids = data.get("response_ids", [])

    if not response_ids:
        raise HTTPException(status_code=400, detail="No response IDs provided")

    # Get responses from database
    responses = db.query(CustomerResponse).filter(
        CustomerResponse.id.in_(response_ids)
    ).all()

    # Prepare messages for batch classification
    messages = [
        {
            "id": str(r.id),
            "text": r.message_body,
            "channel": r.channel,
            "customer_history": {
                "customer_id": r.customer_id,
                "customer_name": r.customer_name,
                "customer_email": r.customer_email,
            },
        }
        for r in responses
    ]

    # Classify batch
    classifier = AIResponseClassifier()
    classifications = await classifier.classify_batch(messages)

    # Update responses with classifications
    for classification in classifications:
        response_id = classification.get("message_id")
        response = next((r for r in responses if str(r.id) == response_id), None)

        if response:
            response.intent = classification.get("intent")
            response.sentiment_score = classification.get("sentiment", {}).get("score", 0.0)
            response.urgency = classification.get("urgency", {}).get("level", "medium")

            if not response.extra_data:
                response.extra_data = {}
            response.extra_data["ai_classification"] = classification

    db.commit()

    return {
        "total_classified": len(classifications),
        "classifications": classifications,
    }


@router.post("/generate-response")
async def generate_ai_response(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Generate AI response for a customer message."""
    response_id = data.get("response_id")
    brand_voice = data.get("brand_voice")
    response_guidelines = data.get("response_guidelines")

    if not response_id:
        raise HTTPException(status_code=400, detail="response_id required")

    # Get the response
    response = db.query(CustomerResponse).filter(
        CustomerResponse.id == response_id
    ).first()

    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

    # Get or create classification
    classification = None
    if response.extra_data and "ai_classification" in response.extra_data:
        classification = response.extra_data["ai_classification"]
    else:
        # Classify first
        classifier = AIResponseClassifier()
        classification = await classifier.classify_response(
            message_text=response.message_body,
            channel=response.channel,
        )

    # Generate response
    classifier = AIResponseClassifier()
    generated = await classifier.generate_response(
        message_text=response.message_body,
        classification=classification,
        response_guidelines=response_guidelines,
        brand_voice=brand_voice,
    )

    if "error" in generated:
        raise HTTPException(status_code=500, detail=generated["error"])

    return {
        "response_id": str(response_id),
        "generated_response": generated,
        "classification": classification,
    }


@router.post("/analyze-objection")
async def analyze_objection(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Analyze customer objection."""
    message_text = data.get("message_text")

    if not message_text:
        raise HTTPException(status_code=400, detail="message_text required")

    classifier = AIResponseClassifier()
    analysis = await classifier.detect_objection_type(message_text)

    if "error" in analysis:
        raise HTTPException(status_code=500, detail=analysis["error"])

    return analysis


@router.post("/analyze-purchase-intent")
async def analyze_purchase_intent(
    data: Dict[str, Any],
    db: Session = Depends(get_db),
):
    """Analyze purchase intent in customer message."""
    message_text = data.get("message_text")
    customer_journey_stage = data.get("customer_journey_stage")

    if not message_text:
        raise HTTPException(status_code=400, detail="message_text required")

    classifier = AIResponseClassifier()
    analysis = await classifier.analyze_purchase_intent(
        message_text=message_text,
        customer_journey_stage=customer_journey_stage,
    )

    if "error" in analysis:
        raise HTTPException(status_code=500, detail=analysis["error"])

    return analysis


@router.get("/sla-alerts")
async def get_sla_alerts(
    tenant_uuid: UUID,
    db: Session = Depends(get_db),
):
    """Get SLA breach alerts."""
    inbox_service = UnifiedInboxService(db)
    alerts = await inbox_service.get_sla_alerts(tenant_uuid)
    return {"alerts": alerts}


@router.get("/analytics")
async def get_inbox_analytics(
    tenant_uuid: UUID,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get inbox analytics."""
    from datetime import datetime

    inbox_service = UnifiedInboxService(db)

    # Parse dates if provided
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None

    analytics = await inbox_service.get_inbox_analytics(
        tenant_uuid=tenant_uuid,
        start_date=start,
        end_date=end,
    )

    return analytics


@router.get("/templates")
async def list_response_templates(
    tenant_uuid: UUID,
    category: str = None,
    db: Session = Depends(get_db),
):
    """List response templates."""
    return {"templates": []}
