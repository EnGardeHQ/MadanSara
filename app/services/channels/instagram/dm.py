"""Instagram DM automation using Meta Graph API."""

from typing import Dict, List, Optional, Any
import os
import httpx
from datetime import datetime


class InstagramDMService:
    """Handles Instagram Direct Message automation via Meta Graph API."""

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    async def send_dm(
        self,
        recipient_ig_id: str,
        message_text: str,
        message_id: str,
    ) -> Dict[str, Any]:
        """
        Send Instagram DM.

        Args:
            recipient_ig_id: Instagram user ID (IGSID)
            message_text: Message content
            message_id: Madan Sara message ID for tracking

        Returns:
            Send result
        """
        if not self.access_token:
            return {"success": False, "error": "Meta access token not configured", "mock": True}

        try:
            async with httpx.AsyncClient() as client:
                # Get Instagram Business Account ID
                ig_account_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")

                if not ig_account_id:
                    return {"success": False, "error": "Instagram account ID not configured"}

                # Send message via Instagram Messaging API
                url = f"{self.base_url}/{ig_account_id}/messages"

                payload = {
                    "recipient": {"id": recipient_ig_id},
                    "message": {"text": message_text},
                    "messaging_type": "MESSAGE_TAG",
                    "tag": "HUMAN_AGENT",  # Required for messages outside 24h window
                    "access_token": self.access_token,
                }

                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "message_id": result.get("message_id"),
                        "recipient_id": result.get("recipient_id"),
                        "provider": "instagram",
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                        "status_code": response.status_code,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_dm_with_media(
        self,
        recipient_ig_id: str,
        message_text: str,
        media_url: str,
        media_type: str = "image",
    ) -> Dict[str, Any]:
        """
        Send Instagram DM with media attachment.

        Args:
            recipient_ig_id: Recipient Instagram ID
            message_text: Message text
            media_url: URL to media file
            media_type: image, video, or audio

        Returns:
            Send result
        """
        if not self.access_token:
            return {"success": False, "error": "Not configured", "mock": True}

        try:
            async with httpx.AsyncClient() as client:
                ig_account_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
                url = f"{self.base_url}/{ig_account_id}/messages"

                # Build attachment payload
                attachment = {
                    "type": media_type,
                    "payload": {"url": media_url}
                }

                payload = {
                    "recipient": {"id": recipient_ig_id},
                    "message": {
                        "text": message_text,
                        "attachment": attachment
                    },
                    "access_token": self.access_token,
                }

                response = await client.post(url, json=payload)

                if response.status_code == 200:
                    result = response.json()
                    return {
                        "success": True,
                        "message_id": result.get("message_id"),
                        "provider": "instagram",
                    }
                else:
                    return {
                        "success": False,
                        "error": response.text,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_user_profile(
        self,
        ig_user_id: str,
    ) -> Dict[str, Any]:
        """
        Get Instagram user profile information.

        Args:
            ig_user_id: Instagram user ID

        Returns:
            User profile data
        """
        if not self.access_token:
            return {"error": "Not configured"}

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{ig_user_id}"
                params = {
                    "fields": "id,username,name,profile_picture_url,followers_count",
                    "access_token": self.access_token,
                }

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": response.text}

        except Exception as e:
            return {"error": str(e)}

    async def check_conversation_eligibility(
        self,
        recipient_ig_id: str,
    ) -> Dict[str, Any]:
        """
        Check if we can message this user.

        Instagram only allows messaging users who have:
        - Messaged the business first, OR
        - Interacted with content (within 24 hours for promotional)

        Args:
            recipient_ig_id: Recipient Instagram ID

        Returns:
            Eligibility status
        """
        # TODO: Implement actual eligibility check via API
        # For now, return permissive
        return {
            "can_message": True,
            "reason": "previous_conversation",
            "messaging_window": "human_agent_tag",
        }

    async def handle_webhook_message(
        self,
        webhook_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Handle incoming Instagram message webhook.

        Args:
            webhook_data: Webhook payload from Meta

        Returns:
            Processed message data
        """
        try:
            entry = webhook_data.get("entry", [{}])[0]
            messaging = entry.get("messaging", [{}])[0]

            sender_id = messaging.get("sender", {}).get("id")
            recipient_id = messaging.get("recipient", {}).get("id")
            timestamp = messaging.get("timestamp")
            message = messaging.get("message", {})

            message_text = message.get("text", "")
            message_id = message.get("mid")
            attachments = message.get("attachments", [])

            return {
                "sender_id": sender_id,
                "recipient_id": recipient_id,
                "timestamp": datetime.fromtimestamp(timestamp / 1000) if timestamp else None,
                "message_text": message_text,
                "message_id": message_id,
                "attachments": attachments,
                "platform": "instagram",
            }

        except Exception as e:
            return {"error": f"Failed to parse webhook: {str(e)}"}

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 25,
    ) -> List[Dict[str, Any]]:
        """
        Get Instagram conversation history.

        Args:
            conversation_id: Instagram conversation ID
            limit: Number of messages to retrieve

        Returns:
            List of messages
        """
        if not self.access_token:
            return []

        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{conversation_id}/messages"
                params = {
                    "fields": "id,created_time,from,to,message",
                    "limit": limit,
                    "access_token": self.access_token,
                }

                response = await client.get(url, params=params)

                if response.status_code == 200:
                    result = response.json()
                    return result.get("data", [])
                else:
                    return []

        except Exception as e:
            return []

    async def mark_as_read(
        self,
        message_id: str,
    ) -> Dict[str, Any]:
        """
        Mark Instagram message as read.

        Args:
            message_id: Message ID to mark as read

        Returns:
            Result
        """
        if not self.access_token:
            return {"success": False, "error": "Not configured"}

        try:
            async with httpx.AsyncClient() as client:
                ig_account_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
                url = f"{self.base_url}/{ig_account_id}/messages"

                payload = {
                    "recipient": {"id": message_id},
                    "sender_action": "mark_seen",
                    "access_token": self.access_token,
                }

                response = await client.post(url, json=payload)

                return {
                    "success": response.status_code == 200,
                    "response": response.text if response.status_code != 200 else None,
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def send_typing_indicator(
        self,
        recipient_ig_id: str,
        typing: bool = True,
    ) -> Dict[str, Any]:
        """
        Send typing indicator to show bot is composing.

        Args:
            recipient_ig_id: Recipient ID
            typing: True to show typing, False to hide

        Returns:
            Result
        """
        if not self.access_token:
            return {"success": False}

        try:
            async with httpx.AsyncClient() as client:
                ig_account_id = os.getenv("META_INSTAGRAM_ACCOUNT_ID")
                url = f"{self.base_url}/{ig_account_id}/messages"

                payload = {
                    "recipient": {"id": recipient_ig_id},
                    "sender_action": "typing_on" if typing else "typing_off",
                    "access_token": self.access_token,
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
        Validate message content against Instagram policies.

        Args:
            message_text: Message to validate

        Returns:
            Validation result
        """
        errors = []

        # Check length (Instagram has 1000 character limit)
        if len(message_text) > 1000:
            errors.append("Message exceeds 1000 character limit")

        # Check for prohibited content (basic check)
        prohibited_words = ["spam", "scam", "free money"]
        for word in prohibited_words:
            if word.lower() in message_text.lower():
                errors.append(f"Message contains prohibited word: {word}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
        }
