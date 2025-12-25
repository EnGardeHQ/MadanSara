"""Facebook Messenger automation using Meta Graph API."""

from typing import Dict, List, Optional, Any
import os
import httpx
from datetime import datetime


class FacebookMessengerService:
    """Handles Facebook Messenger automation via Meta Graph API."""

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.page_access_token = os.getenv("META_PAGE_ACCESS_TOKEN")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    async def send_message(
        self,
        recipient_psid: str,
        message_text: str,
        message_id: str,
    ) -> Dict[str, Any]:
        """
        Send Facebook Messenger message.

        Args:
            recipient_psid: Page-scoped ID (PSID) of recipient
            message_text: Message content
            message_id: Madan Sara message ID for tracking

        Returns:
            Send result
        """
        if not self.page_access_token:
            return {"success": False, "error": "Facebook Page access token not configured", "mock": True}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/me/messages"

                payload = {
                    "recipient": {"id": recipient_psid},
                    "message": {"text": message_text},
                    "messaging_type": "MESSAGE_TAG",
                    "tag": "CONFIRMED_EVENT_UPDATE",  # For messages outside 24h window
                    "access_token": self.page_access_token,
                }

                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "message_id": result.get("message_id"),
                        "recipient_id": result.get("recipient_id"),
                        "provider": "facebook",
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_message_with_quick_replies(
        self,
        recipient_psid: str,
        message_text: str,
        quick_replies: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """
        Send message with quick reply buttons.

        Args:
            recipient_psid: Recipient PSID
            message_text: Message text
            quick_replies: List of quick reply options
                [{"title": "Yes", "payload": "YES"}, ...]

        Returns:
            Send result
        """
        if not self.page_access_token:
            return {"success": False, "error": "Not configured"}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/me/messages"

                quick_reply_list = [
                    {
                        "content_type": "text",
                        "title": qr["title"],
                        "payload": qr["payload"]
                    }
                    for qr in quick_replies
                ]

                payload = {
                    "recipient": {"id": recipient_psid},
                    "message": {
                        "text": message_text,
                        "quick_replies": quick_reply_list
                    },
                    "access_token": self.page_access_token,
                }

                response = await client.post(url, json=payload)

                return {
                    "success": response.status_code == 200,
                    "message_id": response.json().get("message_id") if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_template_message(
        self,
        recipient_psid: str,
        template_type: str,
        elements: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Send structured template message (generic, button, etc.).

        Args:
            recipient_psid: Recipient PSID
            template_type: generic, button, receipt, etc.
            elements: Template elements

        Returns:
            Send result
        """
        if not self.page_access_token:
            return {"success": False, "error": "Not configured"}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/me/messages"

                payload = {
                    "recipient": {"id": recipient_psid},
                    "message": {
                        "attachment": {
                            "type": "template",
                            "payload": {
                                "template_type": template_type,
                                "elements": elements
                            }
                        }
                    },
                    "access_token": self.page_access_token,
                }

                response = await client.post(url, json=payload)

                return {
                    "success": response.status_code == 200,
                    "message_id": response.json().get("message_id") if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_user_profile(
        self,
        user_psid: str,
    ) -> Dict[str, Any]:
        """
        Get Facebook user profile information.

        Args:
            user_psid: User PSID

        Returns:
            User profile data
        """
        if not self.page_access_token:
            return {"error": "Not configured"}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{user_psid}"
                params = {
                    "fields": "first_name,last_name,profile_pic,locale,timezone,gender",
                    "access_token": self.page_access_token,
                }

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.text}

        except Exception as e:
            return {"error": str(e)}

    async def handle_webhook_message(
        self,
        webhook_data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Handle incoming Facebook Messenger webhook.

        Args:
            webhook_data: Webhook payload from Meta

        Returns:
            List of processed messages
        """
        try:
            messages = []

            for entry in webhook_data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    sender_id = messaging_event.get("sender", {}).get("id")
                    recipient_id = messaging_event.get("recipient", {}).get("id")
                    timestamp = messaging_event.get("timestamp")

                    # Handle different event types
                    if "message" in messaging_event:
                        message = messaging_event["message"]
                        messages.append({
                            "type": "message",
                            "sender_id": sender_id,
                            "recipient_id": recipient_id,
                            "timestamp": datetime.fromtimestamp(timestamp / 1000),
                            "message_id": message.get("mid"),
                            "text": message.get("text", ""),
                            "attachments": message.get("attachments", []),
                            "quick_reply": message.get("quick_reply"),
                        })

                    elif "postback" in messaging_event:
                        postback = messaging_event["postback"]
                        messages.append({
                            "type": "postback",
                            "sender_id": sender_id,
                            "payload": postback.get("payload"),
                            "title": postback.get("title"),
                            "timestamp": datetime.fromtimestamp(timestamp / 1000),
                        })

            return messages

        except Exception as e:
            return [{"error": f"Failed to parse webhook: {str(e)}"}]

    async def send_typing_indicator(
        self,
        recipient_psid: str,
        typing: bool = True,
    ) -> Dict[str, Any]:
        """
        Send typing indicator.

        Args:
            recipient_psid: Recipient PSID
            typing: True for typing_on, False for typing_off

        Returns:
            Result
        """
        if not self.page_access_token:
            return {"success": False}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/me/messages"

                payload = {
                    "recipient": {"id": recipient_psid},
                    "sender_action": "typing_on" if typing else "typing_off",
                    "access_token": self.page_access_token,
                }

                response = await client.post(url, json=payload)
                return {"success": response.status_code == 200}

        except:
            return {"success": False}

    async def mark_as_seen(
        self,
        recipient_psid: str,
    ) -> Dict[str, Any]:
        """
        Mark message as seen.

        Args:
            recipient_psid: Recipient PSID

        Returns:
            Result
        """
        if not self.page_access_token:
            return {"success": False}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/me/messages"

                payload = {
                    "recipient": {"id": recipient_psid},
                    "sender_action": "mark_seen",
                    "access_token": self.page_access_token,
                }

                response = await client.post(url, json=payload)
                return {"success": response.status_code == 200}

        except:
            return {"success": False}

    def validate_message_content(
        self,
        message_text: str,
    ) -> Dict[str, Any]:
        """
        Validate message content against Facebook policies.

        Args:
            message_text: Message to validate

        Returns:
            Validation result
        """
        errors = []

        # Check length (2000 character limit for Messenger)
        if len(message_text) > 2000:
            errors.append("Message exceeds 2000 character limit")

        # Check for empty message
        if not message_text.strip():
            errors.append("Message cannot be empty")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }

    async def get_page_insights(
        self,
        page_id: str,
        metrics: List[str],
    ) -> Dict[str, Any]:
        """
        Get Facebook Page insights/analytics.

        Args:
            page_id: Facebook Page ID
            metrics: List of metrics to retrieve

        Returns:
            Insights data
        """
        if not self.page_access_token:
            return {"error": "Not configured"}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{page_id}/insights"
                params = {
                    "metric": ",".join(metrics),
                    "access_token": self.page_access_token,
                }

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.text}

        except Exception as e:
            return {"error": str(e)}
