"""Unit tests for AI Response Classifier."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch

from app.services.ai_classification.classifier import AIResponseClassifier


class TestAIResponseClassifier:
    """Test AI classification functionality."""

    @pytest.fixture
    def classifier(self):
        return AIResponseClassifier()

    @pytest.mark.asyncio
    async def test_classify_purchase_intent(self, classifier):
        """Test classification of purchase intent message."""
        message_text = "I'd like to buy this product. What's the price?"
        channel = "email"

        # Mock Claude API response
        mock_response = {
            "intent": "purchase_intent",
            "intent_confidence": 0.85,
            "sentiment": {
                "score": 0.6,
                "label": "positive",
            },
            "urgency": {
                "level": "high",
                "reason": "Direct purchase inquiry",
            },
            "topics": ["pricing", "product_purchase"],
            "entities": {
                "products": ["this product"],
                "issues": [],
                "requests": ["price information"],
            },
            "next_best_action": {
                "action": "provide_pricing_and_purchase_link",
                "priority": "high",
                "reasoning": "Customer shows clear purchase intent",
            },
            "requires_human": {
                "flag": False,
                "reason": None,
            },
            "suggested_response": {
                "tone": "professional",
                "key_points": ["Provide price", "Share purchase link", "Highlight benefits"],
                "template_suggestion": "purchase_inquiry",
            },
        }

        with patch.object(classifier.client.messages, "create") as mock_create:
            mock_message = Mock()
            mock_message.content = [Mock(text=f"```json\n{json.dumps(mock_response)}\n```")]
            mock_create.return_value = mock_message

            result = await classifier.classify_response(
                message_text=message_text,
                channel=channel,
            )

            assert result["intent"] == "purchase_intent"
            assert result["sentiment"]["score"] > 0
            assert result["urgency"]["level"] == "high"
            assert "classified_at" in result
            assert "model" in result

    @pytest.mark.asyncio
    async def test_classify_complaint(self, classifier):
        """Test classification of complaint message."""
        message_text = "This product is terrible. It broke after one day. I want a refund!"
        channel = "instagram"

        mock_response = {
            "intent": "complaint",
            "intent_confidence": 0.95,
            "sentiment": {
                "score": -0.8,
                "label": "very_negative",
            },
            "urgency": {
                "level": "high",
                "reason": "Customer is very dissatisfied and requesting refund",
            },
            "topics": ["product_quality", "refund_request"],
            "entities": {
                "products": ["this product"],
                "issues": ["broke after one day"],
                "requests": ["refund"],
            },
            "next_best_action": {
                "action": "escalate_to_customer_service",
                "priority": "high",
                "reasoning": "Negative experience requires immediate attention",
            },
            "requires_human": {
                "flag": True,
                "reason": "High-priority complaint with refund request",
            },
            "suggested_response": {
                "tone": "empathetic",
                "key_points": ["Apologize", "Acknowledge issue", "Offer solution"],
                "template_suggestion": "complaint_response",
            },
        }

        with patch.object(classifier.client.messages, "create") as mock_create:
            mock_message = Mock()
            mock_message.content = [Mock(text=json.dumps(mock_response))]
            mock_create.return_value = mock_message

            result = await classifier.classify_response(
                message_text=message_text,
                channel=channel,
            )

            assert result["intent"] == "complaint"
            assert result["sentiment"]["score"] < 0
            assert result["requires_human"]["flag"] is True
            assert result["urgency"]["level"] == "high"

    @pytest.mark.asyncio
    async def test_classify_question(self, classifier):
        """Test classification of simple question."""
        message_text = "What are your business hours?"
        channel = "facebook"

        mock_response = {
            "intent": "question",
            "intent_confidence": 0.9,
            "sentiment": {
                "score": 0.0,
                "label": "neutral",
            },
            "urgency": {
                "level": "low",
                "reason": "Simple informational query",
            },
            "topics": ["business_hours"],
            "entities": {
                "products": [],
                "issues": [],
                "requests": ["business hours information"],
            },
            "next_best_action": {
                "action": "provide_business_hours",
                "priority": "medium",
                "reasoning": "Standard informational request",
            },
            "requires_human": {
                "flag": False,
                "reason": None,
            },
            "suggested_response": {
                "tone": "friendly",
                "key_points": ["Provide hours", "Offer additional help"],
                "template_suggestion": "faq_response",
            },
        }

        with patch.object(classifier.client.messages, "create") as mock_create:
            mock_message = Mock()
            mock_message.content = [Mock(text=json.dumps(mock_response))]
            mock_create.return_value = mock_message

            result = await classifier.classify_response(
                message_text=message_text,
                channel=channel,
            )

            assert result["intent"] == "question"
            assert result["requires_human"]["flag"] is False

    @pytest.mark.asyncio
    async def test_classify_batch(self, classifier):
        """Test batch classification."""
        messages = [
            {"id": "msg_1", "text": "I want to buy this", "channel": "email"},
            {"id": "msg_2", "text": "What's your return policy?", "channel": "instagram"},
        ]

        mock_response_1 = {
            "intent": "purchase_intent",
            "sentiment": {"score": 0.7, "label": "positive"},
            "urgency": {"level": "high"},
        }

        mock_response_2 = {
            "intent": "question",
            "sentiment": {"score": 0.0, "label": "neutral"},
            "urgency": {"level": "medium"},
        }

        with patch.object(classifier, "classify_response", new_callable=AsyncMock) as mock_classify:
            mock_classify.side_effect = [mock_response_1, mock_response_2]

            results = await classifier.classify_batch(messages, max_concurrent=2)

            assert len(results) == 2
            assert results[0]["intent"] == "purchase_intent"
            assert results[1]["intent"] == "question"

    @pytest.mark.asyncio
    async def test_generate_response(self, classifier):
        """Test AI response generation."""
        message_text = "How do I reset my password?"
        classification = {
            "intent": "question",
            "sentiment": {"score": 0.0, "label": "neutral"},
            "urgency": {"level": "medium"},
            "suggested_response": {
                "tone": "helpful",
                "key_points": ["Explain password reset process", "Provide link"],
            },
        }

        mock_generated = {
            "response_text": "To reset your password, click on 'Forgot Password' on the login page. You'll receive an email with instructions.",
            "subject_line": "Password Reset Instructions",
            "call_to_action": "Click here to reset your password",
            "follow_up_needed": False,
            "confidence": 0.9,
            "reasoning": "Standard password reset procedure",
        }

        with patch.object(classifier.client.messages, "create") as mock_create:
            mock_message = Mock()
            mock_message.content = [Mock(text=json.dumps(mock_generated))]
            mock_create.return_value = mock_message

            result = await classifier.generate_response(
                message_text=message_text,
                classification=classification,
                brand_voice="friendly and helpful",
            )

            assert "response_text" in result
            assert result["follow_up_needed"] is False
            assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_detect_objection_type(self, classifier):
        """Test objection type detection."""
        message_text = "Your product is too expensive. I can get similar from CompetitorX for half the price."

        mock_objection = {
            "objection_type": "price",
            "severity": "high",
            "specifics": {
                "mentioned_price": "too expensive",
                "mentioned_competitor": "CompetitorX",
                "mentioned_timeline": None,
            },
            "customer_readiness": "considering",
            "recommended_approach": "Emphasize value proposition and unique features",
            "talking_points": [
                "Highlight quality differences",
                "Explain long-term value",
                "Offer payment plans if applicable",
            ],
            "success_probability": 0.6,
            "next_steps": [
                "Provide value comparison",
                "Share customer testimonials",
                "Offer limited-time discount",
            ],
        }

        with patch.object(classifier.client.messages, "create") as mock_create:
            mock_message = Mock()
            mock_message.content = [Mock(text=json.dumps(mock_objection))]
            mock_create.return_value = mock_message

            result = await classifier.detect_objection_type(message_text)

            assert result["objection_type"] == "price"
            assert result["severity"] == "high"
            assert "CompetitorX" in result["specifics"]["mentioned_competitor"]

    @pytest.mark.asyncio
    async def test_analyze_purchase_intent(self, classifier):
        """Test purchase intent analysis."""
        message_text = "I need this by Friday. Can you ship it overnight?"

        mock_intent = {
            "purchase_intent_score": 0.85,
            "intent_level": "very_high",
            "buying_signals": [
                "Specific timeline (Friday)",
                "Inquiring about shipping options",
                "Using 'need' language",
            ],
            "barriers": [],
            "urgency_indicators": ["Friday deadline", "overnight shipping inquiry"],
            "next_best_offer": "Confirm overnight shipping availability and provide expedited checkout link",
            "recommended_discount": "0",
            "close_probability": 0.8,
            "recommended_action": {
                "action": "send_expedited_purchase_link",
                "timing": "immediate",
                "channel": "email",
            },
        }

        with patch.object(classifier.client.messages, "create") as mock_create:
            mock_message = Mock()
            mock_message.content = [Mock(text=json.dumps(mock_intent))]
            mock_create.return_value = mock_message

            result = await classifier.analyze_purchase_intent(
                message_text=message_text,
                customer_journey_stage="decision",
            )

            assert result["purchase_intent_score"] > 0.8
            assert result["intent_level"] == "very_high"
            assert len(result["urgency_indicators"]) > 0

    @pytest.mark.asyncio
    async def test_fallback_classification(self, classifier):
        """Test fallback classification when AI fails."""
        message_text = "I want to buy this product now!"

        # Mock API error
        with patch.object(classifier.client.messages, "create") as mock_create:
            mock_create.side_effect = Exception("API error")

            result = await classifier.classify_response(
                message_text=message_text,
                channel="email",
            )

            # Should return error dict
            assert "error" in result
            assert "Classification failed" in result["error"]

    def test_fallback_classification_purchase_intent(self, classifier):
        """Test fallback classification detects purchase intent."""
        message_text = "I want to buy this product"

        result = classifier._fallback_classification(message_text, "test_error")

        assert result["intent"] == "purchase_intent"
        assert result["fallback"] is True

    def test_fallback_classification_complaint(self, classifier):
        """Test fallback classification detects complaint."""
        message_text = "This is a terrible product. I have a problem with it."

        result = classifier._fallback_classification(message_text, "test_error")

        assert result["intent"] == "complaint"
        assert result["sentiment"]["score"] < 0

    def test_fallback_classification_question(self, classifier):
        """Test fallback classification detects question."""
        message_text = "How does this work? What should I do?"

        result = classifier._fallback_classification(message_text, "test_error")

        assert result["intent"] == "question"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
