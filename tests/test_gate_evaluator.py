"""Unit tests for GateEvaluator (deterministic rule-based logic).

27 scenarios covering all 6 gates:
- Touch Cap (4 tests)
- Cooling Off (5 tests)
- Dispute (2 tests)
- Hardship (2 tests)
- Unsubscribe (2 tests)
- Escalation Appropriate (9 tests)
- Combined Scenarios (3 tests)
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.api.models.responses import EvaluateGatesResponse
from src.engine.gate_evaluator import GateEvaluator


class TestGateEvaluator:
    """Tests for GateEvaluator deterministic evaluation."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        return GateEvaluator()

    # =========================================================================
    # Touch Cap Gate (4 tests)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_touch_cap_zero_count(self, evaluator, sample_evaluate_gates_request):
        """Test touch cap passes with zero touches."""
        sample_evaluate_gates_request.context.monthly_touch_count = 0
        sample_evaluate_gates_request.context.touch_cap = 10

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["touch_cap"].passed is True

    @pytest.mark.asyncio
    async def test_touch_cap_just_under(self, evaluator, sample_evaluate_gates_request):
        """Test touch cap passes when just under limit."""
        sample_evaluate_gates_request.context.monthly_touch_count = 9
        sample_evaluate_gates_request.context.touch_cap = 10

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["touch_cap"].passed is True

    @pytest.mark.asyncio
    async def test_touch_cap_at_limit(self, evaluator, sample_evaluate_gates_request):
        """Test touch cap fails when at limit."""
        sample_evaluate_gates_request.context.monthly_touch_count = 10
        sample_evaluate_gates_request.context.touch_cap = 10

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["touch_cap"].passed is False
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_touch_cap_over_limit(self, evaluator, sample_evaluate_gates_request):
        """Test touch cap fails when over limit."""
        sample_evaluate_gates_request.context.monthly_touch_count = 15
        sample_evaluate_gates_request.context.touch_cap = 10

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["touch_cap"].passed is False
        assert result.allowed is False

    # =========================================================================
    # Cooling Off Gate (5 tests)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_cooling_off_no_last_touch(self, evaluator, sample_evaluate_gates_request):
        """Test cooling off passes on first contact (no last_touch_at)."""
        sample_evaluate_gates_request.context.communication.last_touch_at = None
        sample_evaluate_gates_request.context.touch_interval_days = 3

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["cooling_off"].passed is True

    @pytest.mark.asyncio
    async def test_cooling_off_sufficient_gap(self, evaluator, sample_evaluate_gates_request):
        """Test cooling off passes with sufficient gap (5 days > 3 interval)."""
        sample_evaluate_gates_request.context.communication.last_touch_at = datetime.now(
            timezone.utc
        ) - timedelta(days=5)
        sample_evaluate_gates_request.context.touch_interval_days = 3

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["cooling_off"].passed is True

    @pytest.mark.asyncio
    async def test_cooling_off_insufficient_gap(self, evaluator, sample_evaluate_gates_request):
        """Test cooling off fails with insufficient gap (1 day < 3 interval)."""
        sample_evaluate_gates_request.context.communication.last_touch_at = datetime.now(
            timezone.utc
        ) - timedelta(days=1)
        sample_evaluate_gates_request.context.touch_interval_days = 3

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["cooling_off"].passed is False

    @pytest.mark.asyncio
    async def test_cooling_off_do_not_contact_future(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test cooling off fails when do_not_contact_until is in future."""
        future_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
        sample_evaluate_gates_request.context.do_not_contact_until = future_date

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["cooling_off"].passed is False

    @pytest.mark.asyncio
    async def test_cooling_off_do_not_contact_past(self, evaluator, sample_evaluate_gates_request):
        """Test cooling off passes when do_not_contact_until is in past."""
        past_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        sample_evaluate_gates_request.context.do_not_contact_until = past_date
        sample_evaluate_gates_request.context.communication.last_touch_at = datetime.now(
            timezone.utc
        ) - timedelta(days=5)
        sample_evaluate_gates_request.context.touch_interval_days = 3

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["cooling_off"].passed is True

    # =========================================================================
    # Dispute Gate (2 tests)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_dispute_inactive(self, evaluator, sample_evaluate_gates_request):
        """Test dispute gate passes when no active dispute."""
        sample_evaluate_gates_request.context.active_dispute = False

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["dispute_active"].passed is True

    @pytest.mark.asyncio
    async def test_dispute_active(self, evaluator, sample_evaluate_gates_request):
        """Test dispute gate fails when dispute is active."""
        sample_evaluate_gates_request.context.active_dispute = True

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["dispute_active"].passed is False
        assert result.allowed is False

    # =========================================================================
    # Hardship Gate (2 tests)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_hardship_not_indicated(self, evaluator, sample_evaluate_gates_request):
        """Test hardship gate passes when not indicated."""
        sample_evaluate_gates_request.context.hardship_indicated = False

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["hardship"].passed is True

    @pytest.mark.asyncio
    async def test_hardship_indicated_passes_with_warning(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test hardship gate passes (with warning) when indicated."""
        sample_evaluate_gates_request.context.hardship_indicated = True

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["hardship"].passed is True
        assert "sensitive tone" in result.gate_results["hardship"].reason.lower()

    # =========================================================================
    # Unsubscribe Gate (2 tests)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_unsubscribe_not_requested(self, evaluator, sample_evaluate_gates_request):
        """Test unsubscribe gate passes when not requested."""
        sample_evaluate_gates_request.context.unsubscribe_requested = False

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["unsubscribe"].passed is True

    @pytest.mark.asyncio
    async def test_unsubscribe_requested(self, evaluator, sample_evaluate_gates_request):
        """Test unsubscribe gate fails when requested."""
        sample_evaluate_gates_request.context.unsubscribe_requested = True

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["unsubscribe"].passed is False
        assert result.allowed is False

    # =========================================================================
    # Escalation Gate (9 tests)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_escalation_first_contact_friendly(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test first contact with friendly_reminder passes."""
        sample_evaluate_gates_request.context.communication.touch_count = 0
        sample_evaluate_gates_request.context.communication.last_tone_used = None
        sample_evaluate_gates_request.proposed_tone = "friendly_reminder"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is True

    @pytest.mark.asyncio
    async def test_escalation_first_contact_firm_fails(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test first contact with firm tone fails."""
        sample_evaluate_gates_request.context.communication.touch_count = 0
        sample_evaluate_gates_request.context.communication.last_tone_used = None
        sample_evaluate_gates_request.proposed_tone = "firm"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is False

    @pytest.mark.asyncio
    async def test_escalation_first_contact_final_notice_fails(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test first contact with final_notice fails."""
        sample_evaluate_gates_request.context.communication.touch_count = 0
        sample_evaluate_gates_request.context.communication.last_tone_used = None
        sample_evaluate_gates_request.proposed_tone = "final_notice"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is False

    @pytest.mark.asyncio
    async def test_escalation_single_step_standard(self, evaluator, sample_evaluate_gates_request):
        """Test single-step escalation professional→firm passes (standard industry)."""
        sample_evaluate_gates_request.context.communication.touch_count = 3
        sample_evaluate_gates_request.context.communication.last_tone_used = "professional"
        sample_evaluate_gates_request.proposed_tone = "firm"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is True

    @pytest.mark.asyncio
    async def test_escalation_double_step_standard_no_broken_promises_fails(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test double-step escalation professional→firm fails (standard, no broken promises).

        Tone order: friendly(0), professional(1), concerned(2), firm(3), final(4).
        professional(1)→firm(3) = jump of 2. Standard allows max 1 (no broken promises).
        """
        sample_evaluate_gates_request.context.communication.touch_count = 3
        sample_evaluate_gates_request.context.communication.last_tone_used = "professional"
        sample_evaluate_gates_request.context.broken_promises_count = 0
        sample_evaluate_gates_request.context.industry = None
        sample_evaluate_gates_request.proposed_tone = "firm"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is False

    @pytest.mark.asyncio
    async def test_escalation_double_step_aggressive_industry(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test double-step escalation passes with aggressive industry (professional→firm, jump=2).

        Tone order: friendly(0), professional(1), concerned(2), firm(3), final(4).
        professional(1)→firm(3) = jump of 2. Aggressive allows max 2.
        """
        from src.api.models.requests import IndustryInfo

        sample_evaluate_gates_request.context.communication.touch_count = 3
        sample_evaluate_gates_request.context.communication.last_tone_used = "professional"
        sample_evaluate_gates_request.context.industry = IndustryInfo(
            code="retail",
            name="Retail",
            typical_dso_days=30,
            alarm_dso_days=45,
            payment_cycle="net30",
            escalation_patience="aggressive",
        )
        sample_evaluate_gates_request.proposed_tone = "firm"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is True

    @pytest.mark.asyncio
    async def test_escalation_single_step_patient_industry(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test single-step escalation firm→final_notice passes with patient industry."""
        from src.api.models.requests import IndustryInfo

        sample_evaluate_gates_request.context.communication.touch_count = 5
        sample_evaluate_gates_request.context.communication.last_tone_used = "firm"
        sample_evaluate_gates_request.context.industry = IndustryInfo(
            code="manufacturing",
            name="Manufacturing",
            typical_dso_days=60,
            alarm_dso_days=90,
            payment_cycle="net60",
            escalation_patience="patient",
        )
        sample_evaluate_gates_request.proposed_tone = "final_notice"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is True

    @pytest.mark.asyncio
    async def test_escalation_de_escalation_allowed(self, evaluator, sample_evaluate_gates_request):
        """Test de-escalation firm→friendly_reminder always passes."""
        sample_evaluate_gates_request.context.communication.touch_count = 3
        sample_evaluate_gates_request.context.communication.last_tone_used = "firm"
        sample_evaluate_gates_request.proposed_tone = "friendly_reminder"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is True

    @pytest.mark.asyncio
    async def test_escalation_double_step_broken_promises_standard(
        self, evaluator, sample_evaluate_gates_request
    ):
        """Test double-step escalation passes with broken promises (professional→firm, jump=2).

        Tone order: friendly(0), professional(1), concerned(2), firm(3), final(4).
        professional(1)→firm(3) = jump of 2. Standard allows 2 with broken promises.
        """
        sample_evaluate_gates_request.context.communication.touch_count = 3
        sample_evaluate_gates_request.context.communication.last_tone_used = "professional"
        sample_evaluate_gates_request.context.broken_promises_count = 2
        sample_evaluate_gates_request.context.industry = None
        sample_evaluate_gates_request.proposed_tone = "firm"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert result.gate_results["escalation_appropriate"].passed is True

    # =========================================================================
    # Combined Scenarios (3 tests)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_combined_all_pass(self, evaluator, sample_evaluate_gates_request):
        """Test all gates pass → allowed=True."""
        sample_evaluate_gates_request.context.monthly_touch_count = 0
        sample_evaluate_gates_request.context.touch_cap = 10
        sample_evaluate_gates_request.context.active_dispute = False
        sample_evaluate_gates_request.context.hardship_indicated = False
        sample_evaluate_gates_request.context.unsubscribe_requested = False
        sample_evaluate_gates_request.context.do_not_contact_until = None
        sample_evaluate_gates_request.context.communication.touch_count = 3
        sample_evaluate_gates_request.context.communication.last_tone_used = "friendly_reminder"
        sample_evaluate_gates_request.proposed_tone = "professional"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert isinstance(result, EvaluateGatesResponse)
        assert result.allowed is True
        assert all(g.passed for g in result.gate_results.values())

    @pytest.mark.asyncio
    async def test_combined_multiple_failures(self, evaluator, sample_evaluate_gates_request):
        """Test multiple gate failures → allowed=False with all failures in results."""
        sample_evaluate_gates_request.context.monthly_touch_count = 10
        sample_evaluate_gates_request.context.touch_cap = 10
        sample_evaluate_gates_request.context.active_dispute = True
        sample_evaluate_gates_request.context.unsubscribe_requested = True

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert isinstance(result, EvaluateGatesResponse)
        assert result.allowed is False
        assert result.gate_results["touch_cap"].passed is False
        assert result.gate_results["dispute_active"].passed is False
        assert result.gate_results["unsubscribe"].passed is False

    @pytest.mark.asyncio
    async def test_combined_hardship_warning_only(self, evaluator, sample_evaluate_gates_request):
        """Test only hardship warning → allowed=True (hardship doesn't block)."""
        sample_evaluate_gates_request.context.monthly_touch_count = 0
        sample_evaluate_gates_request.context.touch_cap = 10
        sample_evaluate_gates_request.context.active_dispute = False
        sample_evaluate_gates_request.context.hardship_indicated = True
        sample_evaluate_gates_request.context.unsubscribe_requested = False
        sample_evaluate_gates_request.context.do_not_contact_until = None
        sample_evaluate_gates_request.context.communication.touch_count = 3
        sample_evaluate_gates_request.context.communication.last_tone_used = "friendly_reminder"
        sample_evaluate_gates_request.proposed_tone = "professional"

        result = await evaluator.evaluate(sample_evaluate_gates_request)

        assert isinstance(result, EvaluateGatesResponse)
        assert result.allowed is True
        assert result.gate_results["hardship"].passed is True
