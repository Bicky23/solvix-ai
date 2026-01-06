"""Unit tests for EmailClassifier."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.engine.classifier import EmailClassifier
from src.api.models.responses import ClassifyResponse


class TestEmailClassifier:
    """Tests for EmailClassifier."""

    @pytest.fixture
    def classifier(self):
        """Create classifier instance."""
        return EmailClassifier()

    @pytest.mark.asyncio
    async def test_classify_hardship_email(self, classifier, sample_classify_request):
        """Test classification of hardship email."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "classification": "HARDSHIP",
            "confidence": 0.92,
            "reasoning": "Customer mentions job loss and requests payment plan",
            "extracted_data": {
                "payment_amount": null,
                "payment_date": null,
                "dispute_reason": null,
                "hardship_type": "job_loss"
            }
        }"""

        with patch.object(classifier.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await classifier.classify(sample_classify_request)
            
            assert isinstance(result, ClassifyResponse)
            assert result.classification == "HARDSHIP"
            assert result.confidence >= 0.9
            assert "job" in result.reasoning.lower() or "hardship" in result.reasoning.lower()
            mock_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_promise_to_pay(self, classifier, sample_classify_request):
        """Test classification of promise to pay email."""
        sample_classify_request.email.body = "I will pay the full amount of £1500 by Friday January 20th."
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "classification": "PROMISE_TO_PAY",
            "confidence": 0.95,
            "reasoning": "Customer commits to specific payment amount and date",
            "extracted_data": {
                "payment_amount": 1500,
                "payment_date": "2024-01-20",
                "dispute_reason": null,
                "hardship_type": null
            }
        }"""

        with patch.object(classifier.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await classifier.classify(sample_classify_request)
            
            assert result.classification == "PROMISE_TO_PAY"
            assert result.extracted_data is not None
            assert result.extracted_data.payment_amount == 1500

    @pytest.mark.asyncio
    async def test_classify_dispute_email(self, classifier, sample_classify_request):
        """Test classification of dispute email."""
        sample_classify_request.email.body = "I never received the goods for invoice #12345. This charge is incorrect."
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "classification": "DISPUTE",
            "confidence": 0.88,
            "reasoning": "Customer claims goods not received and disputes charge",
            "extracted_data": {
                "payment_amount": null,
                "payment_date": null,
                "dispute_reason": "goods_not_received",
                "hardship_type": null
            }
        }"""

        with patch.object(classifier.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await classifier.classify(sample_classify_request)
            
            assert result.classification == "DISPUTE"
            assert result.extracted_data.dispute_reason == "goods_not_received"

    @pytest.mark.asyncio
    async def test_classify_unsubscribe_email(self, classifier, sample_classify_request):
        """Test classification of unsubscribe request."""
        sample_classify_request.email.body = "Please remove me from your mailing list. I do not wish to receive further emails."
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "classification": "UNSUBSCRIBE",
            "confidence": 0.97,
            "reasoning": "Customer explicitly requests removal from mailing list",
            "extracted_data": null
        }"""

        with patch.object(classifier.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await classifier.classify(sample_classify_request)
            
            assert result.classification == "UNSUBSCRIBE"
            assert result.confidence > 0.9

    @pytest.mark.asyncio
    async def test_classify_handles_json_parse_error(self, classifier, sample_classify_request):
        """Test classifier handles malformed LLM response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not valid JSON"

        with patch.object(classifier.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            with pytest.raises(Exception):
                await classifier.classify(sample_classify_request)

    @pytest.mark.asyncio
    async def test_classify_out_of_office(self, classifier, sample_classify_request):
        """Test classification of out of office auto-reply."""
        sample_classify_request.email.body = "I am currently out of the office with no access to email. I will return on January 25th."
        sample_classify_request.email.subject = "Out of Office: Re: Invoice #12345"
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "classification": "OUT_OF_OFFICE",
            "confidence": 0.99,
            "reasoning": "Automatic out of office reply detected",
            "extracted_data": null
        }"""

        with patch.object(classifier.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await classifier.classify(sample_classify_request)
            
            assert result.classification == "OUT_OF_OFFICE"
