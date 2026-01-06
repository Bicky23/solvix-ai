"""Unit tests for GateEvaluator."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.engine.gate_evaluator import GateEvaluator
from src.api.models.responses import EvaluateGatesResponse, GateResult


class TestGateEvaluator:
    """Tests for GateEvaluator."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return GateEvaluator()

    @pytest.mark.asyncio
    async def test_evaluate_all_gates_pass(self, evaluator, sample_evaluate_gates_request):
        """Test evaluation when all gates pass."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "gates": [
                {"gate": "touch_cap", "passed": true, "reason": "3 of 10 touches used"},
                {"gate": "cooling_off", "passed": true, "reason": "5 days since last touch"},
                {"gate": "dispute_active", "passed": true, "reason": "No active dispute"},
                {"gate": "hardship", "passed": true, "reason": "No hardship indicated"},
                {"gate": "unsubscribe", "passed": true, "reason": "Not unsubscribed"},
                {"gate": "escalation_appropriate", "passed": true, "reason": "Normal escalation path"}
            ],
            "overall_allowed": true,
            "blocking_gates": []
        }"""

        with patch.object(evaluator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await evaluator.evaluate(sample_evaluate_gates_request)
            
            assert isinstance(result, EvaluateGatesResponse)
            assert result.overall_allowed is True
            assert len(result.blocking_gates) == 0
            assert len(result.gates) == 6

    @pytest.mark.asyncio
    async def test_evaluate_touch_cap_exceeded(self, evaluator, sample_evaluate_gates_request):
        """Test evaluation when touch cap is exceeded."""
        sample_evaluate_gates_request.context.communication.touch_count = 10
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "gates": [
                {"gate": "touch_cap", "passed": false, "reason": "Touch cap of 10 reached"},
                {"gate": "cooling_off", "passed": true, "reason": "5 days since last touch"},
                {"gate": "dispute_active", "passed": true, "reason": "No active dispute"},
                {"gate": "hardship", "passed": true, "reason": "No hardship indicated"},
                {"gate": "unsubscribe", "passed": true, "reason": "Not unsubscribed"},
                {"gate": "escalation_appropriate", "passed": true, "reason": "Normal escalation path"}
            ],
            "overall_allowed": false,
            "blocking_gates": ["touch_cap"]
        }"""

        with patch.object(evaluator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await evaluator.evaluate(sample_evaluate_gates_request)
            
            assert result.overall_allowed is False
            assert "touch_cap" in result.blocking_gates

    @pytest.mark.asyncio
    async def test_evaluate_active_dispute_blocks(self, evaluator, sample_evaluate_gates_request):
        """Test evaluation when there's an active dispute."""
        sample_evaluate_gates_request.context.active_dispute = True
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "gates": [
                {"gate": "touch_cap", "passed": true, "reason": "3 of 10 touches used"},
                {"gate": "cooling_off", "passed": true, "reason": "5 days since last touch"},
                {"gate": "dispute_active", "passed": false, "reason": "Active dispute must be resolved first"},
                {"gate": "hardship", "passed": true, "reason": "No hardship indicated"},
                {"gate": "unsubscribe", "passed": true, "reason": "Not unsubscribed"},
                {"gate": "escalation_appropriate", "passed": true, "reason": "Normal escalation path"}
            ],
            "overall_allowed": false,
            "blocking_gates": ["dispute_active"]
        }"""

        with patch.object(evaluator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await evaluator.evaluate(sample_evaluate_gates_request)
            
            assert result.overall_allowed is False
            assert "dispute_active" in result.blocking_gates

    @pytest.mark.asyncio
    async def test_evaluate_hardship_blocks_standard_action(self, evaluator, sample_evaluate_gates_request):
        """Test evaluation when hardship is indicated."""
        sample_evaluate_gates_request.context.hardship_indicated = True
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "gates": [
                {"gate": "touch_cap", "passed": true, "reason": "3 of 10 touches used"},
                {"gate": "cooling_off", "passed": true, "reason": "5 days since last touch"},
                {"gate": "dispute_active", "passed": true, "reason": "No active dispute"},
                {"gate": "hardship", "passed": false, "reason": "Hardship case requires special handling"},
                {"gate": "unsubscribe", "passed": true, "reason": "Not unsubscribed"},
                {"gate": "escalation_appropriate", "passed": true, "reason": "Normal escalation path"}
            ],
            "overall_allowed": false,
            "blocking_gates": ["hardship"]
        }"""

        with patch.object(evaluator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await evaluator.evaluate(sample_evaluate_gates_request)
            
            assert result.overall_allowed is False
            assert "hardship" in result.blocking_gates

    @pytest.mark.asyncio
    async def test_evaluate_cooling_off_period(self, evaluator, sample_evaluate_gates_request):
        """Test evaluation during cooling off period."""
        sample_evaluate_gates_request.context.communication.last_touch_at = "2024-01-14T09:00:00Z"  # Yesterday
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "gates": [
                {"gate": "touch_cap", "passed": true, "reason": "3 of 10 touches used"},
                {"gate": "cooling_off", "passed": false, "reason": "Only 1 day since last touch, need 3"},
                {"gate": "dispute_active", "passed": true, "reason": "No active dispute"},
                {"gate": "hardship", "passed": true, "reason": "No hardship indicated"},
                {"gate": "unsubscribe", "passed": true, "reason": "Not unsubscribed"},
                {"gate": "escalation_appropriate", "passed": true, "reason": "Normal escalation path"}
            ],
            "overall_allowed": false,
            "blocking_gates": ["cooling_off"]
        }"""

        with patch.object(evaluator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await evaluator.evaluate(sample_evaluate_gates_request)
            
            assert result.overall_allowed is False
            assert "cooling_off" in result.blocking_gates

    @pytest.mark.asyncio
    async def test_evaluate_multiple_blocking_gates(self, evaluator, sample_evaluate_gates_request):
        """Test evaluation with multiple blocking conditions."""
        sample_evaluate_gates_request.context.active_dispute = True
        sample_evaluate_gates_request.context.communication.touch_count = 10
        
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """{
            "gates": [
                {"gate": "touch_cap", "passed": false, "reason": "Touch cap of 10 reached"},
                {"gate": "cooling_off", "passed": true, "reason": "5 days since last touch"},
                {"gate": "dispute_active", "passed": false, "reason": "Active dispute on account"},
                {"gate": "hardship", "passed": true, "reason": "No hardship indicated"},
                {"gate": "unsubscribe", "passed": true, "reason": "Not unsubscribed"},
                {"gate": "escalation_appropriate", "passed": true, "reason": "Normal escalation path"}
            ],
            "overall_allowed": false,
            "blocking_gates": ["touch_cap", "dispute_active"]
        }"""

        with patch.object(evaluator.llm, "chat_completion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response
            
            result = await evaluator.evaluate(sample_evaluate_gates_request)
            
            assert result.overall_allowed is False
            assert len(result.blocking_gates) == 2
            assert "touch_cap" in result.blocking_gates
            assert "dispute_active" in result.blocking_gates
