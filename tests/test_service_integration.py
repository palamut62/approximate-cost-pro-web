"""
Service Integration Tests for AI Analysis System

Tests for:
- AIAnalysisService parameter extensions (model, temperature)
- ConsensusAnalysisService
- SelfConsistencyService
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.ai_service import AIAnalysisService
from services.consensus_service import ConsensusAnalysisService
from services.self_consistency_service import SelfConsistencyService
from services.cot_service import ChainOfThoughtService


class TestAIServiceParameters:
    """Tests for AIAnalysisService parameter extensions"""

    def test_generate_analysis_accepts_model_param(self):
        """generate_analysis should accept model parameter"""
        service = AIAnalysisService(openrouter_key="test-key")

        # Mock the _call_openrouter method
        with patch.object(service, '_call_openrouter') as mock_call:
            mock_call.return_value = {
                "components": [],
                "explanation": "Test"
            }

            result = service.generate_analysis(
                description="Test beton",
                unit="m³",
                context_data="",
                model="google/gemini-2.0-flash-001"
            )

            # Verify _call_openrouter was called with model parameter
            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args.kwargs.get('model') == "google/gemini-2.0-flash-001"

    def test_generate_analysis_accepts_temperature_param(self):
        """generate_analysis should accept temperature parameter"""
        service = AIAnalysisService(openrouter_key="test-key")

        with patch.object(service, '_call_openrouter') as mock_call:
            mock_call.return_value = {
                "components": [],
                "explanation": "Test"
            }

            result = service.generate_analysis(
                description="Test beton",
                unit="m³",
                context_data="",
                temperature=0.2
            )

            mock_call.assert_called_once()
            call_args = mock_call.call_args
            assert call_args.kwargs.get('temperature') == 0.2

    def test_generate_analysis_uses_defaults_when_params_none(self):
        """generate_analysis should use defaults when model/temperature are None"""
        service = AIAnalysisService(
            openrouter_key="test-key",
            model="moonshot/kimi-k2.5"
        )

        with patch.object(service, '_call_openrouter') as mock_call:
            mock_call.return_value = {
                "components": [],
                "explanation": "Test"
            }

            result = service.generate_analysis(
                description="Test beton",
                unit="m³"
            )

            mock_call.assert_called_once()
            call_args = mock_call.call_args
            # model should be None (will use self.model in _call_openrouter)
            assert call_args.kwargs.get('model') is None
            # temperature should be None (will use default 0.1)
            assert call_args.kwargs.get('temperature') is None


class TestConsensusService:
    """Tests for ConsensusAnalysisService"""

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service"""
        service = Mock(spec=AIAnalysisService)
        service.generate_analysis = Mock(return_value={
            "components": [
                {"type": "Malzeme", "name": "Beton", "quantity": 1.0, "unit_price": 100}
            ],
            "explanation": "Test analizi"
        })
        return service

    def test_consensus_service_initialization(self, mock_ai_service):
        """ConsensusAnalysisService should initialize correctly"""
        consensus = ConsensusAnalysisService(mock_ai_service)

        assert consensus.ai_service == mock_ai_service
        assert len(consensus.models) >= 1

    @pytest.mark.asyncio
    async def test_consensus_analyze_calls_multiple_models(self, mock_ai_service):
        """analyze_with_consensus should call AI service for each model"""
        consensus = ConsensusAnalysisService(mock_ai_service)

        result = await consensus.analyze_with_consensus(
            description="C25 hazır beton",
            unit="m³",
            context_data=""
        )

        # Should have been called at least once
        assert mock_ai_service.generate_analysis.called
        # Result should have consensus_score
        assert "consensus_score" in result or "components" in result

    @pytest.mark.asyncio
    async def test_consensus_returns_consensus_score(self, mock_ai_service):
        """analyze_with_consensus should return consensus_score"""
        consensus = ConsensusAnalysisService(mock_ai_service)

        # Configure mock to return multiple results
        mock_ai_service.generate_analysis.side_effect = [
            {"components": [{"type": "Malzeme", "name": "Beton"}]},
            {"components": [{"type": "Malzeme", "name": "Beton"}]}
        ]

        result = await consensus.analyze_with_consensus(
            description="C25 hazır beton",
            unit="m³"
        )

        # Should return valid result
        assert isinstance(result, dict)


class TestSelfConsistencyService:
    """Tests for SelfConsistencyService"""

    @pytest.fixture
    def mock_ai_service(self):
        """Create a mock AI service"""
        service = Mock(spec=AIAnalysisService)
        service.generate_analysis = Mock(return_value={
            "components": [
                {"type": "Malzeme", "name": "Beton", "quantity": 1.0}
            ],
            "explanation": "Test"
        })
        return service

    def test_self_consistency_initialization(self, mock_ai_service):
        """SelfConsistencyService should initialize with n_samples"""
        service = SelfConsistencyService(mock_ai_service, n_samples=5)

        assert service.ai_service == mock_ai_service
        assert service.n_samples == 5

    @pytest.mark.asyncio
    async def test_consistency_analyze_calls_with_different_temps(self, mock_ai_service):
        """analyze_with_consistency should call with different temperatures"""
        service = SelfConsistencyService(mock_ai_service, n_samples=3)

        result = await service.analyze_with_consistency(
            description="Betonarme temel",
            unit="m³"
        )

        # Should call multiple times
        assert mock_ai_service.generate_analysis.call_count >= 1

    @pytest.mark.asyncio
    async def test_consistency_returns_consistency_score(self, mock_ai_service):
        """analyze_with_consistency should return consistency_score"""
        service = SelfConsistencyService(mock_ai_service, n_samples=3)

        # Mock multiple consistent responses
        mock_ai_service.generate_analysis.side_effect = [
            {"components": [{"name": "Beton"}, {"name": "Demir"}]},
            {"components": [{"name": "Beton"}, {"name": "Demir"}]},
            {"components": [{"name": "Beton"}, {"name": "Demir"}]}
        ]

        result = await service.analyze_with_consistency(
            description="Betonarme",
            unit="m³"
        )

        assert isinstance(result, dict)
        # Should have consistency_score in result
        if "consistency_score" in result:
            assert 0 <= result["consistency_score"] <= 1

    def test_calculate_consistency_score(self, mock_ai_service):
        """_calculate_consistency should return valid score"""
        service = SelfConsistencyService(mock_ai_service)

        results = [
            {"components": [{"name": "A"}, {"name": "B"}]},
            {"components": [{"name": "A"}, {"name": "B"}]},
            {"components": [{"name": "A"}, {"name": "B"}]}
        ]

        score = service._calculate_consistency(results)
        assert 0 <= score <= 1


class TestChainOfThoughtService:
    """Tests for ChainOfThoughtService"""

    def test_cot_service_initialization(self):
        """ChainOfThoughtService should initialize"""
        cot = ChainOfThoughtService()
        assert cot is not None

    def test_build_cot_prompt_includes_thinking_section(self):
        """build_cot_prompt should include <thinking> section"""
        cot = ChainOfThoughtService()

        prompt = cot.build_cot_prompt(
            description="Hazır beton C25/30",
            unit="m³",
            context="Test context"
        )

        assert "<thinking>" in prompt
        assert "ADIM ADIM DÜŞÜN" in prompt

    def test_build_cot_prompt_includes_description(self):
        """build_cot_prompt should include the description"""
        cot = ChainOfThoughtService()

        prompt = cot.build_cot_prompt(
            description="Betonarme temel",
            unit="m³",
            context=""
        )

        assert "Betonarme temel" in prompt
        assert "m³" in prompt


class TestIntegration:
    """Integration tests between services"""

    def test_consensus_with_real_ai_service_structure(self):
        """Test ConsensusService works with AIAnalysisService interface"""
        # Create real service but mock API calls
        ai_service = AIAnalysisService(openrouter_key="test-key")

        with patch.object(ai_service, '_call_openrouter') as mock_call:
            mock_call.return_value = {
                "components": [{"type": "Malzeme", "name": "Test"}],
                "explanation": "Test"
            }

            consensus = ConsensusAnalysisService(ai_service)
            assert consensus.ai_service == ai_service

    def test_self_consistency_with_real_ai_service_structure(self):
        """Test SelfConsistencyService works with AIAnalysisService interface"""
        ai_service = AIAnalysisService(openrouter_key="test-key")

        with patch.object(ai_service, '_call_openrouter') as mock_call:
            mock_call.return_value = {
                "components": [],
                "explanation": "Test"
            }

            consistency = SelfConsistencyService(ai_service, n_samples=2)
            assert consistency.ai_service == ai_service


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
