"""AI-powered response classification using Claude."""

from typing import Dict, List, Optional, Any
import os
import json
from datetime import datetime
from anthropic import Anthropic


class AIResponseClassifier:
    """Classifies customer responses using Claude AI."""

    def __init__(self):
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-3-5-sonnet-20241022"

    async def classify_response(
        self,
        message_text: str,
        channel: str,
        customer_history: Optional[Dict[str, Any]] = None,
        conversation_context: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, Any]:
        """
        Classify customer response with AI.

        Args:
            message_text: Customer message content
            channel: Communication channel (email, instagram, facebook, etc.)
            customer_history: Optional customer history data
            conversation_context: Optional previous messages in conversation

        Returns:
            Classification results
        """
        # Build context for Claude
        context_parts = [
            f"Channel: {channel}",
            f"Message: {message_text}",
        ]

        if customer_history:
            context_parts.append(
                f"Customer History: {json.dumps(customer_history, indent=2)}"
            )

        if conversation_context:
            context_parts.append("Previous Conversation:")
            for msg in conversation_context[-5:]:  # Last 5 messages
                context_parts.append(
                    f"  {msg.get('sender', 'unknown')}: {msg.get('text', '')}"
                )

        prompt = f"""Analyze this customer message and provide a detailed classification.

{chr(10).join(context_parts)}

Provide your analysis in JSON format with the following structure:
{{
  "intent": "one of: purchase_intent, question, objection, complaint, compliment, feedback, unsubscribe, spam, other",
  "intent_confidence": 0.0-1.0,
  "sentiment": {{
    "score": -1.0 to 1.0 (negative to positive),
    "label": "very_negative, negative, neutral, positive, very_positive"
  }},
  "urgency": {{
    "level": "high, medium, low",
    "reason": "explanation of urgency assessment"
  }},
  "topics": ["list of main topics discussed"],
  "entities": {{
    "products": ["mentioned products"],
    "issues": ["mentioned issues or problems"],
    "requests": ["specific requests made"]
  }},
  "next_best_action": {{
    "action": "recommended next action",
    "priority": "high, medium, low",
    "reasoning": "why this action is recommended"
  }},
  "requires_human": {{
    "flag": true/false,
    "reason": "why human intervention is needed (if applicable)"
  }},
  "suggested_response": {{
    "tone": "professional, friendly, empathetic, etc.",
    "key_points": ["points to address in response"],
    "template_suggestion": "which template type would work best"
  }}
}}

Be thorough and accurate. Consider the channel context and customer history when available."""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,  # Lower temperature for more consistent classification
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse Claude's response
            response_text = message.content[0].text

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            classification = json.loads(response_text)

            # Add metadata
            classification["classified_at"] = datetime.utcnow().isoformat()
            classification["model"] = self.model
            classification["raw_message"] = message_text

            return classification

        except json.JSONDecodeError as e:
            # Fallback to basic classification
            return self._fallback_classification(message_text, str(e))
        except Exception as e:
            return {"error": f"Classification failed: {str(e)}"}

    async def classify_batch(
        self,
        messages: List[Dict[str, Any]],
        max_concurrent: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple messages in batch.

        Args:
            messages: List of message dicts with 'text' and 'channel'
            max_concurrent: Maximum concurrent API calls

        Returns:
            List of classification results
        """
        import asyncio

        async def classify_one(msg: Dict[str, Any]) -> Dict[str, Any]:
            result = await self.classify_response(
                message_text=msg.get("text", ""),
                channel=msg.get("channel", "unknown"),
                customer_history=msg.get("customer_history"),
                conversation_context=msg.get("conversation_context"),
            )
            result["message_id"] = msg.get("id")
            return result

        # Process in batches to avoid rate limits
        results = []
        for i in range(0, len(messages), max_concurrent):
            batch = messages[i : i + max_concurrent]
            batch_results = await asyncio.gather(
                *[classify_one(msg) for msg in batch]
            )
            results.extend(batch_results)

        return results

    async def generate_response(
        self,
        message_text: str,
        classification: Dict[str, Any],
        response_guidelines: Optional[Dict[str, Any]] = None,
        brand_voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate AI response based on classification.

        Args:
            message_text: Original customer message
            classification: Classification results from classify_response()
            response_guidelines: Optional brand-specific guidelines
            brand_voice: Optional brand voice description

        Returns:
            Generated response
        """
        # Build response generation prompt
        context_parts = [
            f"Customer Message: {message_text}",
            f"Intent: {classification.get('intent')}",
            f"Sentiment: {classification.get('sentiment', {}).get('label')}",
            f"Urgency: {classification.get('urgency', {}).get('level')}",
        ]

        if brand_voice:
            context_parts.append(f"Brand Voice: {brand_voice}")

        if response_guidelines:
            context_parts.append(
                f"Response Guidelines: {json.dumps(response_guidelines, indent=2)}"
            )

        suggested_tone = classification.get("suggested_response", {}).get("tone", "professional")
        key_points = classification.get("suggested_response", {}).get("key_points", [])

        prompt = f"""Generate a customer service response to this message.

{chr(10).join(context_parts)}

Key Points to Address:
{chr(10).join(f"- {point}" for point in key_points)}

Tone: {suggested_tone}

Generate a response that:
1. Addresses the customer's intent and concerns
2. Matches the specified tone and brand voice
3. Is appropriate for the urgency level
4. Follows the response guidelines
5. Is professional and helpful

Provide your response in JSON format:
{{
  "response_text": "the actual response message",
  "subject_line": "suggested subject line (if email)",
  "call_to_action": "suggested CTA (if applicable)",
  "follow_up_needed": true/false,
  "follow_up_timeline": "when to follow up (if needed)",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of the response approach"
}}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.7,  # Higher temperature for more natural responses
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            generated = json.loads(response_text)
            generated["generated_at"] = datetime.utcnow().isoformat()
            generated["model"] = self.model

            return generated

        except Exception as e:
            return {"error": f"Response generation failed: {str(e)}"}

    async def detect_objection_type(
        self,
        message_text: str,
    ) -> Dict[str, Any]:
        """
        Detect specific objection types for sales responses.

        Args:
            message_text: Customer message

        Returns:
            Objection analysis
        """
        prompt = f"""Analyze this customer objection and classify it:

Message: {message_text}

Classify the objection type and provide handling recommendations in JSON:
{{
  "objection_type": "price, timing, competitor, need, authority, trust, other",
  "severity": "low, medium, high",
  "specifics": {{
    "mentioned_price": "if price mentioned",
    "mentioned_competitor": "if competitor mentioned",
    "mentioned_timeline": "if timeline mentioned"
  }},
  "customer_readiness": "not_ready, considering, ready_with_concerns, ready",
  "recommended_approach": "how to address this objection",
  "talking_points": ["list of points to address"],
  "success_probability": 0.0-1.0,
  "next_steps": ["recommended next steps"]
}}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            return json.loads(response_text)

        except Exception as e:
            return {"error": f"Objection detection failed: {str(e)}"}

    async def analyze_purchase_intent(
        self,
        message_text: str,
        customer_journey_stage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze purchase intent signals.

        Args:
            message_text: Customer message
            customer_journey_stage: Current journey stage (awareness, consideration, decision)

        Returns:
            Purchase intent analysis
        """
        context = f"Customer Journey Stage: {customer_journey_stage}" if customer_journey_stage else ""

        prompt = f"""Analyze the purchase intent in this customer message:

Message: {message_text}
{context}

Provide analysis in JSON format:
{{
  "purchase_intent_score": 0.0-1.0,
  "intent_level": "none, low, medium, high, very_high",
  "buying_signals": ["list of detected buying signals"],
  "barriers": ["list of detected barriers to purchase"],
  "urgency_indicators": ["indicators of time sensitivity"],
  "next_best_offer": "what offer or information to provide next",
  "recommended_discount": "suggested discount level if applicable (0-30%)",
  "close_probability": 0.0-1.0,
  "recommended_action": {{
    "action": "specific action to take",
    "timing": "immediate, within_24h, within_week",
    "channel": "best channel for follow-up"
  }}
}}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            return json.loads(response_text)

        except Exception as e:
            return {"error": f"Purchase intent analysis failed: {str(e)}"}

    def _fallback_classification(
        self,
        message_text: str,
        error_detail: str,
    ) -> Dict[str, Any]:
        """
        Fallback classification using basic rules when AI fails.

        Args:
            message_text: Message text
            error_detail: Error that caused fallback

        Returns:
            Basic classification
        """
        message_lower = message_text.lower()

        # Basic intent detection
        intent = "other"
        if any(word in message_lower for word in ["buy", "purchase", "order", "price"]):
            intent = "purchase_intent"
        elif any(word in message_lower for word in ["?", "how", "what", "when", "why"]):
            intent = "question"
        elif any(word in message_lower for word in ["complaint", "issue", "problem", "wrong"]):
            intent = "complaint"
        elif any(word in message_lower for word in ["unsubscribe", "stop", "remove"]):
            intent = "unsubscribe"
        elif any(word in message_lower for word in ["spam", "scam", "fake"]):
            intent = "spam"

        # Basic sentiment
        sentiment_score = 0.0
        if any(word in message_lower for word in ["love", "great", "excellent", "amazing"]):
            sentiment_score = 0.8
        elif any(word in message_lower for word in ["good", "thanks", "thank you"]):
            sentiment_score = 0.5
        elif any(word in message_lower for word in ["bad", "poor", "disappointed"]):
            sentiment_score = -0.5
        elif any(word in message_lower for word in ["terrible", "awful", "worst", "hate"]):
            sentiment_score = -0.8

        # Basic urgency
        urgency = "low"
        if any(word in message_lower for word in ["urgent", "asap", "immediately", "emergency"]):
            urgency = "high"
        elif any(word in message_lower for word in ["soon", "quickly", "waiting"]):
            urgency = "medium"

        return {
            "intent": intent,
            "intent_confidence": 0.6,
            "sentiment": {
                "score": sentiment_score,
                "label": "neutral",
            },
            "urgency": {
                "level": urgency,
                "reason": "Basic keyword detection",
            },
            "topics": [],
            "entities": {},
            "next_best_action": {
                "action": "manual_review",
                "priority": "medium",
                "reasoning": "AI classification failed, requires manual review",
            },
            "requires_human": {
                "flag": True,
                "reason": f"AI classification error: {error_detail}",
            },
            "fallback": True,
            "error_detail": error_detail,
        }
