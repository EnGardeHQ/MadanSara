"""Main Orchestrator - Coordinates all outreach components for intelligent multi-channel messaging."""

from typing import Dict, List, Optional, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.outreach import OutreachCampaign, OutreachMessage, OutreachStatus, ChannelType
from app.services.orchestrator.router import ChannelRouter
from app.services.orchestrator.channel_selector import ChannelSelector
from app.services.orchestrator.deduplicator import MessageDeduplicator
from app.services.orchestrator.budget_manager import BudgetManager
from app.services.orchestrator.scheduler import SendTimeScheduler


class OutreachOrchestrator:
    """
    Main orchestrator coordinating all outreach operations.

    This is the primary entry point for sending multi-channel outreach messages.
    It coordinates routing, deduplication, budget management, and scheduling.
    """

    def __init__(self, db: Session):
        self.db = db
        self.router = ChannelRouter(db)
        self.selector = ChannelSelector(db)
        self.deduplicator = MessageDeduplicator(db)
        self.budget_manager = BudgetManager(db)
        self.scheduler = SendTimeScheduler(db)

    async def send_outreach(
        self,
        campaign: OutreachCampaign,
        recipient_id: str,
        recipient_profile: Dict[str, Any],
        content: Dict[str, str],
        force_send: bool = False,
    ) -> Dict[str, Any]:
        """
        Orchestrate sending an outreach message.

        This is the main method that coordinates all orchestration steps:
        1. Deduplication check
        2. Channel selection
        3. Budget verification
        4. Send time scheduling
        5. Message creation

        Args:
            campaign: OutreachCampaign instance
            recipient_id: Unique recipient identifier
            recipient_profile: Recipient data (contact info, preferences, history)
            content: Message content templates for each channel
            force_send: Skip some safety checks (use carefully)

        Returns:
            Dict with status, message_id, channel_used, scheduled_at, etc.
        """
        # Step 1: Deduplication check
        if not force_send:
            dup_check = await self.deduplicator.check_duplicate(
                tenant_uuid=campaign.tenant_uuid,
                recipient_id=recipient_id,
                campaign_id=campaign.id,
                lookback_hours=24,
            )

            if dup_check["is_duplicate"]:
                return {
                    "status": "blocked",
                    "reason": "duplicate",
                    "details": dup_check,
                }

            # Frequency cap check
            freq_check = await self.deduplicator.apply_frequency_cap(
                tenant_uuid=campaign.tenant_uuid,
                recipient_id=recipient_id,
            )

            if not freq_check["can_send"]:
                return {
                    "status": "blocked",
                    "reason": "frequency_cap",
                    "details": freq_check,
                }

        # Step 2: Channel selection
        available_channels = campaign.channels
        contact_info = recipient_profile.get("contact_info", {})

        # Get channel routing decision
        routing = await self.router.route_with_fallback(
            campaign=campaign,
            recipient_id=recipient_id,
            available_channels=available_channels,
            recipient_preferences=recipient_profile.get("preferences"),
            recipient_contact_info=contact_info,
            max_attempts=3,
        )

        if not routing.get("primary_channel"):
            return {
                "status": "failed",
                "reason": "no_viable_channel",
                "details": routing,
            }

        selected_channel = routing["primary_channel"]

        # Step 3: Budget check
        if not force_send:
            budget_check = await self.budget_manager.check_budget_available(
                campaign=campaign,
                channel=selected_channel,
                estimated_cost=0.001,  # TODO: Get from pricing config
            )

            if not budget_check["can_send"]:
                return {
                    "status": "blocked",
                    "reason": "budget_exceeded",
                    "details": budget_check,
                }

            # Daily budget check
            daily_check = await self.budget_manager.check_daily_spend_limit(
                campaign=campaign,
                channel=selected_channel,
            )

            if not daily_check["can_send"]:
                return {
                    "status": "blocked",
                    "reason": "daily_budget_exceeded",
                    "details": daily_check,
                }

        # Step 4: Daily limit check
        if not force_send:
            limit_check = await self.scheduler.check_daily_limit(
                campaign=campaign,
                recipient_id=recipient_id,
            )

            if not limit_check["can_send"]:
                return {
                    "status": "blocked",
                    "reason": "daily_limit_reached",
                    "details": limit_check,
                }

        # Step 5: Calculate optimal send time
        send_time = await self.scheduler.get_optimal_send_time(
            campaign=campaign,
            recipient_profile=recipient_profile,
            channel=selected_channel,
        )

        # Step 6: Create outreach message record
        message = await self._create_message_record(
            campaign=campaign,
            recipient_id=recipient_id,
            recipient_profile=recipient_profile,
            channel=selected_channel,
            content=content.get(selected_channel, content.get("default", "")),
            scheduled_at=send_time,
            routing_info=routing,
        )

        # Step 7: Record budget spend (if applicable)
        if campaign.budget_total:
            await self.budget_manager.record_spend(
                campaign_id=campaign.id,
                channel=selected_channel,
                amount=0.001,  # TODO: Get from pricing config
            )

        return {
            "status": "scheduled" if send_time > datetime.utcnow() else "queued",
            "message_id": str(message.id),
            "channel": selected_channel,
            "scheduled_at": send_time,
            "fallback_channels": routing.get("fallback_chain", []),
            "routing_reason": routing.get("routing_reason"),
        }

    async def _create_message_record(
        self,
        campaign: OutreachCampaign,
        recipient_id: str,
        recipient_profile: Dict[str, Any],
        channel: str,
        content: str,
        scheduled_at: datetime,
        routing_info: Dict[str, Any],
    ) -> OutreachMessage:
        """Create database record for outreach message."""
        contact_info = recipient_profile.get("contact_info", {})

        # Generate deduplication key
        dedup_key = await self.deduplicator.generate_dedup_key(
            tenant_uuid=campaign.tenant_uuid,
            recipient_id=recipient_id,
            campaign_id=campaign.id,
            channel=channel,
        )

        # Create message
        message = OutreachMessage(
            campaign_id=campaign.id,
            tenant_uuid=campaign.tenant_uuid,
            recipient_id=recipient_id,
            recipient_email=contact_info.get("email"),
            recipient_phone=contact_info.get("phone"),
            recipient_social_handle=contact_info.get(f"{channel}_handle"),
            recipient_name=recipient_profile.get("name"),
            channel=ChannelType(channel),
            content=content,
            scheduled_at=scheduled_at,
            status=OutreachStatus.SCHEDULED if scheduled_at > datetime.utcnow() else OutreachStatus.PENDING,
            is_primary_channel=True,
            deduplication_key=dedup_key,
            fallback_from_channel=None,
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        return message

    async def process_fallback(
        self,
        original_message_id: UUID,
        failure_reason: str,
    ) -> Dict[str, Any]:
        """
        Process fallback when primary channel fails.

        Args:
            original_message_id: ID of failed message
            failure_reason: Why the message failed

        Returns:
            Result of fallback attempt
        """
        # Get original message
        original_message = self.db.query(OutreachMessage).filter(
            OutreachMessage.id == original_message_id
        ).first()

        if not original_message:
            return {"status": "failed", "reason": "original_message_not_found"}

        # Get campaign
        campaign = self.db.query(OutreachCampaign).filter(
            OutreachCampaign.id == original_message.campaign_id
        ).first()

        if not campaign:
            return {"status": "failed", "reason": "campaign_not_found"}

        # TODO: Implement fallback logic
        # 1. Get next channel from routing chain
        # 2. Create new message with fallback channel
        # 3. Mark original message as failed with fallback initiated

        return {
            "status": "fallback_not_implemented",
            "original_message_id": str(original_message_id),
            "failure_reason": failure_reason,
        }

    async def send_batch(
        self,
        campaign: OutreachCampaign,
        recipients: List[Dict[str, Any]],
        content_templates: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Send outreach to multiple recipients with intelligent batching.

        Args:
            campaign: Campaign instance
            recipients: List of recipient profiles
            content_templates: Content templates per channel

        Returns:
            Batch results summary
        """
        results = {
            "total": len(recipients),
            "scheduled": 0,
            "blocked": 0,
            "failed": 0,
            "details": [],
        }

        for recipient in recipients:
            result = await self.send_outreach(
                campaign=campaign,
                recipient_id=recipient.get("id"),
                recipient_profile=recipient,
                content=content_templates,
                force_send=False,
            )

            if result["status"] in ["scheduled", "queued"]:
                results["scheduled"] += 1
            elif result["status"] == "blocked":
                results["blocked"] += 1
            else:
                results["failed"] += 1

            results["details"].append({
                "recipient_id": recipient.get("id"),
                "status": result["status"],
                "channel": result.get("channel"),
                "reason": result.get("reason"),
            })

        return results

    async def get_orchestration_status(
        self,
        campaign_id: UUID,
    ) -> Dict[str, Any]:
        """Get current orchestration status for a campaign."""
        campaign = self.db.query(OutreachCampaign).filter(
            OutreachCampaign.id == campaign_id
        ).first()

        if not campaign:
            return {"error": "campaign_not_found"}

        # Get budget status
        budget_status = await self.budget_manager.get_budget_analytics(campaign_id)

        # Get daily limit status
        limit_status = await self.scheduler.check_daily_limit(campaign)

        # Get pacing recommendation
        pacing = await self.budget_manager.get_budget_pacing_recommendation(campaign)

        return {
            "campaign_id": str(campaign_id),
            "campaign_status": campaign.status,
            "budget": budget_status,
            "daily_limit": limit_status,
            "pacing": pacing,
            "total_sent": campaign.messages_sent,
            "total_delivered": campaign.messages_delivered,
            "total_opened": campaign.messages_opened,
            "total_clicked": campaign.messages_clicked,
        }
