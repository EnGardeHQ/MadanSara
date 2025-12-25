"""Email customer service - Automated email response handling."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from uuid import UUID
import email
from email import policy
from email.parser import BytesParser
import anthropic
import os

from app.models.responses import CustomerResponse, ResponseIntent, ResponseUrgency


class EmailCustomerService:
    """Handles automated customer service via email."""

    def __init__(self):
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if self.anthropic_api_key:
            self.claude = anthropic.Anthropic(api_key=self.anthropic_api_key)
        else:
            self.claude = None

    async def parse_incoming_email(
        self,
        raw_email: bytes,
    ) -> Dict[str, Any]:
        """
        Parse incoming email message.

        Args:
            raw_email: Raw email bytes

        Returns:
            Parsed email data
        """
        try:
            msg = BytesParser(policy=policy.default).parsebytes(raw_email)

            # Extract basic fields
            from_addr = msg.get("From", "")
            to_addr = msg.get("To", "")
            subject = msg.get("Subject", "")
            message_id = msg.get("Message-ID", "")
            in_reply_to = msg.get("In-Reply-To")

            # Extract body
            body_text = ""
            body_html = ""

            if msg.is_multipart():
                for part in msg.iter_parts():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body_text = part.get_content()
                    elif content_type == "text/html":
                        body_html = part.get_content()
            else:
                body_text = msg.get_content()

            return {
                "from": from_addr,
                "to": to_addr,
                "subject": subject,
                "message_id": message_id,
                "in_reply_to": in_reply_to,
                "body_text": body_text,
                "body_html": body_html,
                "is_reply": in_reply_to is not None,
            }

        except Exception as e:
            return {"error": f"Failed to parse email: {str(e)}"}

    async def classify_email_intent(
        self,
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Classify customer email intent using Claude.

        Args:
            subject: Email subject
            body: Email body

        Returns:
            Classification with intent, sentiment, urgency
        """
        if not self.claude:
            return {
                "intent": ResponseIntent.OTHER,
                "confidence": 0.0,
                "sentiment": 0.0,
                "urgency": ResponseUrgency.MEDIUM,
            }

        try:
            prompt = f"""Classify this customer email:

Subject: {subject}

Body:
{body}

Provide:
1. Primary intent (purchase, question, objection, complaint, compliment, unsubscribe, spam, other)
2. Sentiment score (-1.0 to 1.0, where -1 is very negative, 0 is neutral, 1 is very positive)
3. Urgency level (high, medium, low)
4. Key topics or issues mentioned
5. Confidence score (0.0 to 1.0)

Respond in JSON format:
{{
    "intent": "question",
    "sentiment": 0.5,
    "urgency": "medium",
    "topics": ["billing", "subscription"],
    "confidence": 0.85
}}"""

            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse Claude's response
            response_text = message.content[0].text

            # Try to extract JSON
            import json
            import re

            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                return {
                    "intent": ResponseIntent(result.get("intent", "other")),
                    "sentiment": float(result.get("sentiment", 0.0)),
                    "urgency": ResponseUrgency(result.get("urgency", "medium")),
                    "topics": result.get("topics", []),
                    "confidence": float(result.get("confidence", 0.5)),
                }

            return {
                "intent": ResponseIntent.OTHER,
                "confidence": 0.0,
                "sentiment": 0.0,
                "urgency": ResponseUrgency.MEDIUM,
            }

        except Exception as e:
            return {
                "intent": ResponseIntent.OTHER,
                "confidence": 0.0,
                "sentiment": 0.0,
                "urgency": ResponseUrgency.MEDIUM,
                "error": str(e),
            }

    async def generate_response(
        self,
        customer_email: str,
        customer_name: Optional[str],
        intent: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate AI response to customer email.

        Args:
            customer_email: Customer's email content
            customer_name: Customer name
            intent: Classified intent
            context: Additional context (order info, account status, etc.)

        Returns:
            Generated response
        """
        if not self.claude:
            return {
                "response": "Thank you for your email. We'll get back to you shortly.",
                "confidence": 0.0,
            }

        try:
            context_str = ""
            if context:
                context_str = f"\n\nContext:\n{json.dumps(context, indent=2)}"

            prompt = f"""You are a helpful customer service representative for En Garde.

Generate a professional, empathetic email response to this customer inquiry:

Customer Name: {customer_name or "Valued Customer"}
Intent: {intent}

Customer's Email:
{customer_email}
{context_str}

Guidelines:
- Be professional and empathetic
- Address their specific concern
- Keep response concise (2-3 paragraphs)
- End with a clear call-to-action if needed
- Use a warm, friendly tone

Generate the response:"""

            message = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            return {
                "response": response_text,
                "confidence": 0.85,  # High confidence for Claude-generated responses
                "requires_approval": self._requires_human_approval(intent),
            }

        except Exception as e:
            return {
                "response": "Thank you for contacting us. We'll review your message and respond shortly.",
                "confidence": 0.0,
                "error": str(e),
            }

    def _requires_human_approval(self, intent: str) -> bool:
        """Determine if response requires human approval."""
        # High-risk intents should be reviewed by humans
        high_risk_intents = [
            ResponseIntent.COMPLAINT,
            ResponseIntent.OBJECTION,
            ResponseIntent.UNSUBSCRIBE,
        ]

        return intent in high_risk_intents

    async def detect_spam(
        self,
        from_email: str,
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        """
        Detect if email is spam.

        Args:
            from_email: Sender email
            subject: Email subject
            body: Email body

        Returns:
            Spam detection result
        """
        spam_indicators = 0
        reasons = []

        # Simple spam detection heuristics
        spam_keywords = [
            "viagra", "casino", "lottery", "prize", "winner",
            "click here now", "limited time", "act now", "free money"
        ]

        subject_lower = subject.lower()
        body_lower = body.lower()

        # Check for spam keywords
        for keyword in spam_keywords:
            if keyword in subject_lower or keyword in body_lower:
                spam_indicators += 1
                reasons.append(f"Contains spam keyword: {keyword}")

        # Check for excessive caps
        if subject.isupper() and len(subject) > 10:
            spam_indicators += 1
            reasons.append("Subject in all caps")

        # Check for suspicious domain
        if from_email:
            domain = from_email.split("@")[-1].lower()
            suspicious_tlds = [".xyz", ".top", ".club", ".work"]
            if any(domain.endswith(tld) for tld in suspicious_tlds):
                spam_indicators += 1
                reasons.append(f"Suspicious domain: {domain}")

        is_spam = spam_indicators >= 2

        return {
            "is_spam": is_spam,
            "spam_score": spam_indicators,
            "reasons": reasons,
        }

    async def auto_respond(
        self,
        customer_response: CustomerResponse,
        auto_approve: bool = False,
    ) -> Dict[str, Any]:
        """
        Automatically respond to customer email.

        Args:
            customer_response: CustomerResponse instance
            auto_approve: Skip HITL approval

        Returns:
            Response status
        """
        # Generate response
        response_data = await self.generate_response(
            customer_email=customer_response.message_body,
            customer_name=customer_response.customer_name,
            intent=customer_response.intent.value if customer_response.intent else "other",
        )

        # Check if approval needed
        if response_data.get("requires_approval") and not auto_approve:
            return {
                "status": "awaiting_approval",
                "response": response_data["response"],
                "confidence": response_data["confidence"],
            }

        # Send response (would integrate with email sending here)
        # TODO: Actually send the email via SendGrid

        return {
            "status": "sent",
            "response": response_data["response"],
            "confidence": response_data["confidence"],
        }

    async def handle_unsubscribe(
        self,
        email: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Handle unsubscribe request.

        Args:
            email: Email to unsubscribe
            reason: Optional unsubscribe reason

        Returns:
            Unsubscribe status
        """
        # TODO: Update user preferences in database
        # Mark as unsubscribed, update suppression list

        return {
            "unsubscribed": True,
            "email": email,
            "reason": reason,
        }

    async def get_response_templates(
        self,
        intent: str,
    ) -> List[Dict[str, str]]:
        """
        Get pre-approved response templates for intent.

        Args:
            intent: Response intent

        Returns:
            List of templates
        """
        # Common response templates
        templates = {
            ResponseIntent.QUESTION: [
                {
                    "name": "General Question",
                    "subject": "Re: Your Question",
                    "body": "Hi {{name}},\n\nThank you for reaching out. {{answer}}\n\nBest regards,\nEn Garde Team"
                }
            ],
            ResponseIntent.COMPLAINT: [
                {
                    "name": "Apology & Resolution",
                    "subject": "Re: Your Concern",
                    "body": "Hi {{name}},\n\nWe sincerely apologize for {{issue}}. We're taking steps to {{resolution}}.\n\nThank you for your patience.\nEn Garde Team"
                }
            ],
            ResponseIntent.PURCHASE: [
                {
                    "name": "Purchase Assistance",
                    "subject": "Re: Your Order",
                    "body": "Hi {{name}},\n\nGreat choice! {{product_info}}\n\n{{next_steps}}\n\nEn Garde Team"
                }
            ],
        }

        return templates.get(intent, [])
