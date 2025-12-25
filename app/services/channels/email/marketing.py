"""Email marketing - Newsletter and promotional email automation."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content, Personalization
from jinja2 import Template

from app.models.outreach import OutreachMessage, ChannelTemplate


class EmailMarketingService:
    """Handles marketing email campaigns (newsletters, promotions, announcements)."""

    def __init__(self):
        self.sendgrid_api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@engarde.com")
        self.from_name = os.getenv("SENDGRID_FROM_NAME", "En Garde")

        if self.sendgrid_api_key:
            self.client = SendGridAPIClient(self.sendgrid_api_key)
        else:
            self.client = None

    async def send_newsletter(
        self,
        message: OutreachMessage,
        recipient_email: str,
        subject: str,
        content_html: str,
        content_text: Optional[str] = None,
        personalization_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send a marketing newsletter email.

        Args:
            message: OutreachMessage instance
            recipient_email: Recipient email address
            subject: Email subject line
            content_html: HTML content
            content_text: Plain text fallback
            personalization_data: Variables for template rendering

        Returns:
            Dict with send status and details
        """
        if not self.client:
            return {
                "success": False,
                "error": "SendGrid API key not configured",
                "mock": True,
            }

        try:
            # Render personalized content
            if personalization_data:
                subject = self._render_template(subject, personalization_data)
                content_html = self._render_template(content_html, personalization_data)
                if content_text:
                    content_text = self._render_template(content_text, personalization_data)

            # Create email message
            mail = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(recipient_email),
                subject=subject,
                html_content=Content("text/html", content_html),
            )

            if content_text:
                mail.add_content(Content("text/plain", content_text))

            # Add tracking parameters
            mail.tracking_settings = self._get_tracking_settings(message.id)

            # Add custom args for analytics
            mail.custom_args = {
                "message_id": str(message.id),
                "campaign_id": str(message.campaign_id),
                "tenant_uuid": str(message.tenant_uuid),
            }

            # Send via SendGrid
            response = self.client.send(mail)

            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get("X-Message-Id"),
                "provider": "sendgrid",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "provider": "sendgrid",
            }

    async def send_promotional_email(
        self,
        message: OutreachMessage,
        recipient_email: str,
        subject: str,
        template_id: Optional[str] = None,
        template_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send promotional email using SendGrid dynamic template.

        Args:
            message: OutreachMessage instance
            recipient_email: Recipient email
            subject: Email subject
            template_id: SendGrid template ID
            template_data: Data for dynamic template

        Returns:
            Send status
        """
        if not self.client:
            return {"success": False, "error": "SendGrid not configured", "mock": True}

        try:
            mail = Mail(
                from_email=Email(self.from_email, self.from_name),
                to_emails=To(recipient_email),
            )

            # Use dynamic template if provided
            if template_id:
                mail.template_id = template_id
                if template_data:
                    mail.dynamic_template_data = template_data
            else:
                mail.subject = subject

            # Tracking and analytics
            mail.tracking_settings = self._get_tracking_settings(message.id)
            mail.custom_args = {
                "message_id": str(message.id),
                "campaign_id": str(message.campaign_id),
            }

            response = self.client.send(mail)

            return {
                "success": True,
                "status_code": response.status_code,
                "message_id": response.headers.get("X-Message-Id"),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_batch_newsletter(
        self,
        messages: List[OutreachMessage],
        subject: str,
        content_html: str,
        content_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send newsletter to multiple recipients in batch.

        Uses SendGrid batch sending for efficiency.

        Args:
            messages: List of OutreachMessage instances
            subject: Email subject
            content_html: HTML content
            content_text: Plain text content

        Returns:
            Batch send results
        """
        if not self.client:
            return {"success": False, "error": "SendGrid not configured"}

        results = {
            "total": len(messages),
            "sent": 0,
            "failed": 0,
            "errors": [],
        }

        # SendGrid allows up to 1000 recipients per API call
        batch_size = 1000

        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]

            try:
                # Create personalization for each recipient
                mail = Mail(
                    from_email=Email(self.from_email, self.from_name),
                    subject=subject,
                    html_content=Content("text/html", content_html),
                )

                if content_text:
                    mail.add_content(Content("text/plain", content_text))

                for msg in batch:
                    if not msg.recipient_email:
                        results["failed"] += 1
                        continue

                    personalization = Personalization()
                    personalization.add_to(To(msg.recipient_email))

                    # Add personalization data
                    if msg.personalization_data:
                        for key, value in msg.personalization_data.items():
                            personalization.add_substitution(f"-{key}-", str(value))

                    # Add custom args per recipient
                    personalization.custom_args = {
                        "message_id": str(msg.id),
                        "recipient_id": msg.recipient_id,
                    }

                    mail.add_personalization(personalization)

                # Send batch
                response = self.client.send(mail)

                if response.status_code in [200, 202]:
                    results["sent"] += len(batch)
                else:
                    results["failed"] += len(batch)
                    results["errors"].append(f"Batch {i//batch_size + 1} failed")

            except Exception as e:
                results["failed"] += len(batch)
                results["errors"].append(f"Batch {i//batch_size + 1}: {str(e)}")

        results["success"] = results["failed"] == 0
        return results

    def _render_template(self, template_str: str, data: Dict[str, Any]) -> str:
        """Render Jinja2 template with data."""
        template = Template(template_str)
        return template.render(**data)

    def _get_tracking_settings(self, message_id: UUID) -> Dict[str, Any]:
        """Get SendGrid tracking settings."""
        return {
            "click_tracking": {"enable": True, "enable_text": False},
            "open_tracking": {"enable": True, "substitution_tag": "%open-track%"},
            "subscription_tracking": {"enable": True},
        }

    async def get_email_analytics(
        self,
        message_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Get email analytics from SendGrid.

        Args:
            message_id: Message ID to query
            start_date: Analytics start date
            end_date: Analytics end date

        Returns:
            Email analytics data
        """
        # TODO: Implement SendGrid Stats API integration
        # This would query SendGrid's stats API for delivery, opens, clicks
        return {
            "message_id": str(message_id),
            "delivered": 0,
            "opens": 0,
            "unique_opens": 0,
            "clicks": 0,
            "unique_clicks": 0,
            "bounces": 0,
            "spam_reports": 0,
            "unsubscribes": 0,
        }

    async def handle_webhook(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle SendGrid webhook events.

        Events: delivered, open, click, bounce, spam_report, unsubscribe

        Args:
            event_data: Webhook event data from SendGrid

        Returns:
            Processing result
        """
        event_type = event_data.get("event")
        message_id = event_data.get("message_id")
        timestamp = event_data.get("timestamp")

        # TODO: Update OutreachMessage in database based on event
        # - delivered: Update delivered_at
        # - open: Update opened_at, increment open_count
        # - click: Update clicked_at, increment click_count, track URL
        # - bounce: Update status to BOUNCED
        # - spam_report: Update status, flag account
        # - unsubscribe: Update recipient preferences

        return {
            "processed": True,
            "event_type": event_type,
            "message_id": message_id,
        }

    async def generate_subject_line_variants(
        self,
        base_subject: str,
        variant_count: int = 3,
    ) -> List[str]:
        """
        Generate A/B test variants for subject lines.

        Uses Claude to generate compelling alternatives.

        Args:
            base_subject: Original subject line
            variant_count: Number of variants to generate

        Returns:
            List of subject line variants
        """
        # TODO: Integrate with Claude API for subject line generation
        # For now, return basic variants
        return [
            base_subject,
            f"🎯 {base_subject}",
            f"{base_subject} - Limited Time",
        ][:variant_count]
