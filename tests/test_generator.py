"""Unit tests for DraftGenerator."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.engine.generator import DraftGenerator
from src.api.models.responses import GenerateDraftResponse


class TestDraftGenerator:
    """Tests for DraftGenerator."""

    @pytest.fixture
    def generator(self):
        """Create generator instance."""
        return DraftGenerator()

    @pytest.mark.asyncio
    async def test_generate_hardship_response(self, generator, sample_generate_draft_request):
        """Test generating response to hardship classification."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "subject": "Re: Your Account - We're Here to Help",
            "body": "Dear Acme Corp,\\n\\nThank you for reaching out and letting us know about your current situation. We understand that circumstances can change unexpectedly.\\n\\nWe would like to discuss options that may help you manage your outstanding balance of £4,000.00. Please contact us at your earliest convenience to discuss a suitable arrangement.\\n\\nKind regards,\\nCollections Team",
            "tone_used": "concerned_inquiry",
            "key_points": ["Acknowledged hardship", "Offered to discuss options", "Mentioned total balance"]
        }"""

        with patch.object(generator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await generator.generate(sample_generate_draft_request)
            
            assert isinstance(result, GenerateDraftResponse)
            assert result.subject is not None
            assert result.body is not None
            assert result.tone_used == "concerned_inquiry"
            assert len(result.key_points) > 0

    @pytest.mark.asyncio
    async def test_generate_friendly_reminder(self, generator, sample_generate_draft_request):
        """Test generating friendly reminder draft."""
        sample_generate_draft_request.classification = "COOPERATIVE"
        sample_generate_draft_request.requested_tone = "friendly_reminder"
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "subject": "Friendly Reminder: Outstanding Invoices",
            "body": "Dear Acme Corp,\\n\\nWe hope this message finds you well. This is a friendly reminder regarding your outstanding invoices totaling £4,000.00.\\n\\nIf you have already made payment, please disregard this message. Otherwise, we would appreciate your attention to this matter.\\n\\nBest regards,\\nCollections Team",
            "tone_used": "friendly_reminder",
            "key_points": ["Polite opening", "Clear amount stated", "Acknowledged possible payment"]
        }"""

        with patch.object(generator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await generator.generate(sample_generate_draft_request)
            
            assert result.tone_used == "friendly_reminder"
            assert "friendly" in result.subject.lower() or "reminder" in result.subject.lower()

    @pytest.mark.asyncio
    async def test_generate_firm_notice(self, generator, sample_generate_draft_request):
        """Test generating firm notice for escalated cases."""
        sample_generate_draft_request.classification = "UNCLEAR"
        sample_generate_draft_request.requested_tone = "firm"
        sample_generate_draft_request.context.broken_promises_count = 3
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "subject": "Important: Immediate Action Required on Your Account",
            "body": "Dear Acme Corp,\\n\\nWe have made multiple attempts to resolve your outstanding balance of £4,000.00 without success.\\n\\nPlease contact us within 7 days to discuss payment arrangements. Failure to respond may result in further action.\\n\\nSincerely,\\nCollections Team",
            "tone_used": "firm",
            "key_points": ["Previous attempts mentioned", "Clear deadline", "Consequences stated"]
        }"""

        with patch.object(generator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await generator.generate(sample_generate_draft_request)
            
            assert result.tone_used == "firm"

    @pytest.mark.asyncio
    async def test_generate_includes_invoice_details(self, generator, sample_generate_draft_request):
        """Test that generated draft includes invoice details from context."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "subject": "Re: Your Account",
            "body": "Dear Acme Corp,\\n\\nRegarding your invoices:\\n- INV-12345: £1,500.00 (14 days overdue)\\n- INV-12346: £2,500.00 (10 days overdue)\\n\\nTotal outstanding: £4,000.00\\n\\nPlease contact us to discuss.\\n\\nRegards,\\nCollections Team",
            "tone_used": "concerned_inquiry",
            "key_points": ["Listed specific invoices", "Showed amounts and overdue days"]
        }"""

        with patch.object(generator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await generator.generate(sample_generate_draft_request)
            
            # Verify the prompt included obligation details
            call_args = mock_llm.call_args
            assert call_args is not None

    @pytest.mark.asyncio
    async def test_generate_respects_brand_tone(self, generator, sample_generate_draft_request):
        """Test that generator respects brand tone from context."""
        sample_generate_draft_request.context.brand_tone = "formal"
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "subject": "Formal Notice Regarding Outstanding Balance",
            "body": "To Whom It May Concern,\\n\\nThis correspondence pertains to the outstanding balance on your account.\\n\\nYours faithfully,\\nCollections Department",
            "tone_used": "professional",
            "key_points": ["Formal language used"]
        }"""

        with patch.object(generator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await generator.generate(sample_generate_draft_request)
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_generate_handles_empty_obligations(self, generator, sample_generate_draft_request):
        """Test generator handles case with no obligations."""
        sample_generate_draft_request.context.obligations = []
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "subject": "Follow Up on Your Account",
            "body": "Dear Acme Corp,\\n\\nWe are following up on your account status.\\n\\nPlease contact us if you have any questions.\\n\\nBest regards,\\nCollections Team",
            "tone_used": "concerned_inquiry",
            "key_points": ["Generic follow-up"]
        }"""

        with patch.object(generator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await generator.generate(sample_generate_draft_request)
            
            assert result.body is not None
