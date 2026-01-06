"""API integration tests for Solvix AI Engine."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health endpoint returns OK."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestClassifyEndpoint:
    """Tests for /classify endpoint."""

    def test_classify_requires_email(self, client):
        """Test classify endpoint requires email field."""
        response = client.post("/classify", json={})
        
        assert response.status_code == 422

    def test_classify_requires_context(self, client):
        """Test classify endpoint requires context field."""
        response = client.post("/classify", json={
            "email": {
                "subject": "Test",
                "body": "Test body",
                "sender": "test@example.com"
            }
        })
        
        assert response.status_code == 422

    @patch("src.api.routes.classify.EmailClassifier")
    def test_classify_success(self, mock_classifier_class, client, sample_classify_request):
        """Test successful classification."""
        mock_classifier = MagicMock()
        mock_classifier.classify = AsyncMock(return_value=MagicMock(
            classification="HARDSHIP",
            confidence=0.92,
            reasoning="Job loss mentioned",
            extracted_data=None
        ))
        mock_classifier_class.return_value = mock_classifier
        
        response = client.post("/classify", json=sample_classify_request.model_dump())
        
        assert response.status_code == 200
        data = response.json()
        assert "classification" in data


class TestGenerateEndpoint:
    """Tests for /generate endpoint."""

    def test_generate_requires_context(self, client):
        """Test generate endpoint requires context field."""
        response = client.post("/generate", json={
            "classification": "HARDSHIP"
        })
        
        assert response.status_code == 422

    def test_generate_requires_classification(self, client, sample_case_context):
        """Test generate endpoint requires classification field."""
        response = client.post("/generate", json={
            "context": sample_case_context.model_dump()
        })
        
        assert response.status_code == 422

    @patch("src.api.routes.generate.DraftGenerator")
    def test_generate_success(self, mock_generator_class, client, sample_generate_draft_request):
        """Test successful draft generation."""
        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(return_value=MagicMock(
            subject="Re: Your Account",
            body="Dear Customer,\n\nThank you for reaching out.",
            tone_used="concerned_inquiry",
            key_points=["Acknowledged hardship"]
        ))
        mock_generator_class.return_value = mock_generator
        
        response = client.post("/generate", json=sample_generate_draft_request.model_dump())
        
        assert response.status_code == 200
        data = response.json()
        assert "subject" in data
        assert "body" in data


class TestGatesEndpoint:
    """Tests for /gates endpoint."""

    def test_gates_requires_context(self, client):
        """Test gates endpoint requires context field."""
        response = client.post("/gates", json={
            "proposed_action": "send_email"
        })
        
        assert response.status_code == 422

    @patch("src.api.routes.gates.GateEvaluator")
    def test_gates_success(self, mock_evaluator_class, client, sample_evaluate_gates_request):
        """Test successful gate evaluation."""
        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(return_value=MagicMock(
            gates=[],
            overall_allowed=True,
            blocking_gates=[]
        ))
        mock_evaluator_class.return_value = mock_evaluator
        
        response = client.post("/gates", json=sample_evaluate_gates_request.model_dump())
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_allowed" in data
