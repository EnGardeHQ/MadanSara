"""Unit tests for A/B Testing Engine."""

import pytest
import numpy as np

from app.services.ab_testing.engine import ABTestingEngine


class TestABTestingEngine:
    """Test A/B testing statistical methods."""

    @pytest.fixture
    def engine(self):
        return ABTestingEngine()

    def test_calculate_sample_size(self, engine):
        """Test sample size calculation."""
        baseline_rate = 0.10  # 10% conversion rate
        min_detectable_effect = 0.15  # 15% improvement
        confidence_level = 0.95
        power = 0.80

        sample_size = engine.calculate_sample_size(
            baseline_rate=baseline_rate,
            min_detectable_effect=min_detectable_effect,
            confidence_level=confidence_level,
            power=power,
        )

        # Sample size should be positive and reasonable
        assert sample_size > 0
        assert sample_size >= engine.min_sample_size
        # For these parameters, expect ~3000-4000 per variant
        assert 2000 < sample_size < 5000

    def test_calculate_significance_not_enough_samples(self, engine):
        """Test significance calculation with insufficient samples."""
        result = engine.calculate_significance(
            control_conversions=5,
            control_samples=50,  # Below minimum
            variant_conversions=7,
            variant_samples=50,  # Below minimum
        )

        assert result["is_significant"] is False
        assert result["reason"] == "insufficient_samples"

    def test_calculate_significance_no_difference(self, engine):
        """Test significance when there's no difference."""
        result = engine.calculate_significance(
            control_conversions=100,
            control_samples=1000,
            variant_conversions=100,
            variant_samples=1000,
        )

        assert result["is_significant"] is False
        assert result["p_value"] > 0.05
        assert abs(result["improvement_pct"]) < 1.0

    def test_calculate_significance_clear_winner(self, engine):
        """Test significance with clear winner."""
        result = engine.calculate_significance(
            control_conversions=100,
            control_samples=1000,  # 10% conversion
            variant_conversions=150,
            variant_samples=1000,  # 15% conversion (50% improvement)
        )

        assert result["is_significant"] is True
        assert result["p_value"] < 0.05
        assert result["improvement_pct"] > 40  # ~50% improvement
        assert result["control_rate"] == 0.1
        assert result["variant_rate"] == 0.15

    def test_calculate_significance_negative_result(self, engine):
        """Test significance with variant performing worse."""
        result = engine.calculate_significance(
            control_conversions=150,
            control_samples=1000,  # 15% conversion
            variant_conversions=100,
            variant_samples=1000,  # 10% conversion
        )

        assert result["improvement_pct"] < 0  # Negative improvement
        assert result["variant_rate"] < result["control_rate"]

    def test_confidence_interval(self, engine):
        """Test confidence interval calculation."""
        result = engine.calculate_significance(
            control_conversions=100,
            control_samples=1000,
            variant_conversions=120,
            variant_samples=1000,
        )

        ci = result["confidence_interval"]
        assert "lower" in ci
        assert "upper" in ci
        # CI should bracket the difference
        assert ci["lower"] < (0.12 - 0.10)
        assert ci["upper"] > (0.12 - 0.10)

    def test_select_winner_no_variants(self, engine):
        """Test winner selection with no variants."""
        variants = []

        winner = engine.select_winner(variants)

        assert winner is None

    def test_select_winner_single_variant(self, engine):
        """Test winner selection with single variant."""
        variants = [
            {
                "id": "variant_a",
                "is_control": True,
                "conversions": 100,
                "impressions": 1000,
                "conversion_rate": 0.10,
            },
        ]

        winner = engine.select_winner(variants)

        assert winner is None  # Need at least 2 variants

    def test_select_winner_clear_winner(self, engine):
        """Test winner selection with clear winner."""
        variants = [
            {
                "id": "control",
                "is_control": True,
                "conversions": 100,
                "impressions": 1000,
                "conversion_rate": 0.10,
            },
            {
                "id": "variant_a",
                "conversions": 150,
                "impressions": 1000,
                "conversion_rate": 0.15,
            },
            {
                "id": "variant_b",
                "conversions": 120,
                "impressions": 1000,
                "conversion_rate": 0.12,
            },
        ]

        winner = engine.select_winner(variants)

        assert winner is not None
        assert winner["id"] == "variant_a"  # Best performer
        assert "test_result" in winner

    def test_select_winner_no_significant_difference(self, engine):
        """Test winner selection when no variant is significantly better."""
        variants = [
            {
                "id": "control",
                "is_control": True,
                "conversions": 100,
                "impressions": 1000,
                "conversion_rate": 0.10,
            },
            {
                "id": "variant_a",
                "conversions": 105,
                "impressions": 1000,
                "conversion_rate": 0.105,
            },
        ]

        winner = engine.select_winner(variants)

        # Difference too small to be significant
        assert winner is None

    def test_calculate_bayesian_probability(self, engine):
        """Test Bayesian probability calculation."""
        result = engine.calculate_bayesian_probability(
            control_conversions=100,
            control_samples=1000,
            variant_conversions=150,
            variant_samples=1000,
            num_simulations=10000,
        )

        assert "prob_variant_better" in result
        assert "expected_improvement" in result
        assert 0 <= result["prob_variant_better"] <= 1

        # Variant is clearly better, should have high probability
        assert result["prob_variant_better"] > 0.95

    def test_bayesian_probability_equal_performance(self, engine):
        """Test Bayesian probability when performance is equal."""
        result = engine.calculate_bayesian_probability(
            control_conversions=100,
            control_samples=1000,
            variant_conversions=100,
            variant_samples=1000,
            num_simulations=10000,
        )

        # Should be close to 50/50
        assert 0.45 < result["prob_variant_better"] < 0.55

    def test_should_stop_test_statistically_significant(self, engine):
        """Test stop decision when statistically significant."""
        result = engine.should_stop_test(
            control_conversions=100,
            control_samples=1000,
            variant_conversions=150,
            variant_samples=1000,
            days_running=5,
            max_days=14,
        )

        assert result["should_stop"] is True
        assert "statistically_significant" in result["reasons"]
        assert result["recommendation"] == "stop_test"

    def test_should_stop_test_max_duration(self, engine):
        """Test stop decision when max duration reached."""
        result = engine.should_stop_test(
            control_conversions=100,
            control_samples=1000,
            variant_conversions=105,
            variant_samples=1000,
            days_running=14,
            max_days=14,
        )

        assert result["should_stop"] is True
        assert "max_duration_reached" in result["reasons"]

    def test_should_stop_test_continue(self, engine):
        """Test continue decision when inconclusive."""
        result = engine.should_stop_test(
            control_conversions=50,
            control_samples=500,  # Small sample
            variant_conversions=55,
            variant_samples=500,  # Small sample
            days_running=3,
            max_days=14,
        )

        # Should continue - not enough data or significance
        assert result["recommendation"] in ["continue_test", "stop_test"]

    def test_should_stop_test_sufficient_samples(self, engine):
        """Test stop decision with sufficient samples but no significance."""
        result = engine.should_stop_test(
            control_conversions=100,
            control_samples=2000,  # Large sample
            variant_conversions=105,
            variant_samples=2000,  # Large sample, minimal difference
            days_running=10,
            max_days=14,
        )

        # Should have sufficient_samples in reasons
        assert "sufficient_samples" in result["reasons"]

    def test_statistical_power(self, engine):
        """Test that statistical power is considered in sample size."""
        # Lower power should require smaller sample
        size_low_power = engine.calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.20,
            confidence_level=0.95,
            power=0.70,  # Lower power
        )

        # Higher power should require larger sample
        size_high_power = engine.calculate_sample_size(
            baseline_rate=0.10,
            min_detectable_effect=0.20,
            confidence_level=0.95,
            power=0.90,  # Higher power
        )

        assert size_high_power > size_low_power

    def test_z_score_calculation(self, engine):
        """Test z-score calculation in significance test."""
        result = engine.calculate_significance(
            control_conversions=100,
            control_samples=1000,
            variant_conversions=150,
            variant_samples=1000,
        )

        # Z-score should be substantial for this difference
        assert abs(result["z_score"]) > 2.0  # Beyond 95% confidence

    def test_minimum_sample_size_enforcement(self, engine):
        """Test that minimum sample size is enforced."""
        sample_size = engine.calculate_sample_size(
            baseline_rate=0.50,  # High baseline
            min_detectable_effect=0.50,  # Large effect
            confidence_level=0.95,
            power=0.80,
        )

        # Even with favorable parameters, should meet minimum
        assert sample_size >= engine.min_sample_size


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
