"""Unit tests for GateEvaluator (deterministic rule-based logic)."""

import pytest

from src.api.models.responses import EvaluateGatesResponse
from src.engine.gate_evaluator import GateEvaluator


class TestGateEvaluator:
    """Tests for GateEvaluator deterministic evaluation."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return GateEvaluator()

    @pytest.mark.asyncio
    async def test_evaluate_touch_cap_exceeded(self, evaluator, sample_evaluate_gates_request):
        """Test blocking when touch cap is exceeded."""
        # Setup context where touch count equals cap
        sample_evaluate_gates_request.context.monthly_touch_count = 10
        sample_evaluate_gates_request.context.touch_cap = 10

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert isinstance(result, EvaluateGatesResponse)
        assert result.gate_results["touch_cap"].passed is False
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_evaluate_active_dispute(self, evaluator, sample_evaluate_gates_request):
        """Test blocking when dispute is active."""
        sample_evaluate_gates_request.context.active_dispute = True

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert isinstance(result, EvaluateGatesResponse)
        assert result.gate_results["dispute_active"].passed is False
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_evaluate_allowed(self, evaluator, sample_evaluate_gates_request):
        """Test allowing when all gates pass."""
        # Ensure all gates should pass
        sample_evaluate_gates_request.context.monthly_touch_count = 0
        sample_evaluate_gates_request.context.touch_cap = 10
        sample_evaluate_gates_request.context.active_dispute = False
        sample_evaluate_gates_request.context.hardship_indicated = False

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert isinstance(result, EvaluateGatesResponse)
        assert result.allowed is True
        assert result.gate_results["touch_cap"].passed is True
        assert result.gate_results["dispute_active"].passed is True
        assert result.gate_results["hardship"].passed is True
