"""A/B Testing engine with statistical significance calculation."""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from uuid import UUID
from scipy import stats
import numpy as np


class ABTestingEngine:
    """Manages A/B tests and calculates statistical significance."""

    def __init__(self):
        self.min_sample_size = 100  # Minimum samples per variant
        self.confidence_level = 0.95  # 95% confidence
        self.min_detectable_effect = 0.10  # 10% minimum effect

    def calculate_sample_size(
        self,
        baseline_rate: float,
        min_detectable_effect: float,
        confidence_level: float = 0.95,
        power: float = 0.80,
    ) -> int:
        """
        Calculate required sample size for A/B test.

        Args:
            baseline_rate: Current conversion rate (e.g., 0.10 for 10%)
            min_detectable_effect: Minimum effect to detect (e.g., 0.15 for 15% improvement)
            confidence_level: Confidence level (default 95%)
            power: Statistical power (default 80%)

        Returns:
            Required sample size per variant
        """
        # Z-scores for confidence and power
        z_alpha = stats.norm.ppf(1 - (1 - confidence_level) / 2)
        z_beta = stats.norm.ppf(power)

        # Expected rates
        p1 = baseline_rate
        p2 = baseline_rate * (1 + min_detectable_effect)

        # Pooled probability
        p_pooled = (p1 + p2) / 2

        # Sample size calculation
        numerator = (z_alpha * np.sqrt(2 * p_pooled * (1 - p_pooled)) +
                    z_beta * np.sqrt(p1 * (1 - p1) + p2 * (1 - p2))) ** 2

        denominator = (p2 - p1) ** 2

        sample_size = int(np.ceil(numerator / denominator))

        return max(sample_size, self.min_sample_size)

    def calculate_significance(
        self,
        control_conversions: int,
        control_samples: int,
        variant_conversions: int,
        variant_samples: int,
    ) -> Dict[str, Any]:
        """
        Calculate statistical significance using two-proportion z-test.

        Args:
            control_conversions: Number of conversions in control
            control_samples: Total samples in control
            variant_conversions: Number of conversions in variant
            variant_samples: Total samples in variant

        Returns:
            Statistical test results
        """
        # Check minimum sample size
        if control_samples < self.min_sample_size or variant_samples < self.min_sample_size:
            return {
                "is_significant": False,
                "reason": "insufficient_samples",
                "min_required": self.min_sample_size,
            }

        # Calculate conversion rates
        control_rate = control_conversions / control_samples
        variant_rate = variant_conversions / variant_samples

        # Pooled probability
        pooled_p = (control_conversions + variant_conversions) / (control_samples + variant_samples)

        # Standard error
        se = np.sqrt(pooled_p * (1 - pooled_p) * (1/control_samples + 1/variant_samples))

        # Z-score
        z_score = (variant_rate - control_rate) / se

        # P-value (two-tailed test)
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        # Confidence interval for difference
        diff = variant_rate - control_rate
        margin_of_error = stats.norm.ppf(1 - (1 - self.confidence_level) / 2) * se
        ci_lower = diff - margin_of_error
        ci_upper = diff + margin_of_error

        # Improvement percentage
        improvement = ((variant_rate - control_rate) / control_rate) * 100 if control_rate > 0 else 0

        # Is significant?
        is_significant = p_value < (1 - self.confidence_level)

        return {
            "is_significant": is_significant,
            "p_value": round(p_value, 4),
            "z_score": round(z_score, 4),
            "control_rate": round(control_rate, 4),
            "variant_rate": round(variant_rate, 4),
            "improvement_pct": round(improvement, 2),
            "confidence_interval": {
                "lower": round(ci_lower, 4),
                "upper": round(ci_upper, 4),
            },
            "confidence_level": self.confidence_level,
        }

    def select_winner(
        self,
        variants: List[Dict[str, Any]],
        metric: str = "conversion_rate",
    ) -> Optional[Dict[str, Any]]:
        """
        Select winning variant based on statistical significance.

        Args:
            variants: List of variant results
            metric: Metric to optimize (conversion_rate, click_rate, etc.)

        Returns:
            Winning variant or None if no clear winner
        """
        if len(variants) < 2:
            return None

        # Find control variant
        control = next((v for v in variants if v.get("is_control")), variants[0])

        # Test each variant against control
        winners = []

        for variant in variants:
            if variant["id"] == control["id"]:
                continue

            # Calculate significance
            result = self.calculate_significance(
                control_conversions=control.get("conversions", 0),
                control_samples=control.get("impressions", 0),
                variant_conversions=variant.get("conversions", 0),
                variant_samples=variant.get("impressions", 0),
            )

            if result["is_significant"] and result["improvement_pct"] > 0:
                variant["test_result"] = result
                winners.append(variant)

        # Return best performer
        if winners:
            return max(winners, key=lambda v: v.get("conversion_rate", 0))

        return None

    def calculate_bayesian_probability(
        self,
        control_conversions: int,
        control_samples: int,
        variant_conversions: int,
        variant_samples: int,
        num_simulations: int = 10000,
    ) -> Dict[str, Any]:
        """
        Calculate Bayesian probability that variant is better.

        Args:
            control_conversions: Control conversions
            control_samples: Control samples
            variant_conversions: Variant conversions
            variant_samples: Variant samples
            num_simulations: Number of Monte Carlo simulations

        Returns:
            Bayesian analysis results
        """
        # Beta distributions (conjugate prior for binomial)
        control_alpha = control_conversions + 1
        control_beta = control_samples - control_conversions + 1

        variant_alpha = variant_conversions + 1
        variant_beta = variant_samples - variant_conversions + 1

        # Monte Carlo simulation
        control_samples_mc = np.random.beta(control_alpha, control_beta, num_simulations)
        variant_samples_mc = np.random.beta(variant_alpha, variant_beta, num_simulations)

        # Probability variant is better
        prob_variant_better = np.mean(variant_samples_mc > control_samples_mc)

        # Expected improvement
        expected_improvement = np.mean(variant_samples_mc - control_samples_mc)

        return {
            "prob_variant_better": round(prob_variant_better, 4),
            "expected_improvement": round(expected_improvement, 4),
            "control_mean": round(np.mean(control_samples_mc), 4),
            "variant_mean": round(np.mean(variant_samples_mc), 4),
        }

    def should_stop_test(
        self,
        control_conversions: int,
        control_samples: int,
        variant_conversions: int,
        variant_samples: int,
        days_running: int,
        max_days: int = 14,
    ) -> Dict[str, bool]:
        """
        Determine if A/B test should be stopped.

        Args:
            control_conversions: Control conversions
            control_samples: Control samples
            variant_conversions: Variant conversions
            variant_samples: Variant samples
            days_running: Days test has been running
            max_days: Maximum days to run test

        Returns:
            Stop decision with reasons
        """
        reasons = []

        # Check if statistically significant
        sig_result = self.calculate_significance(
            control_conversions, control_samples,
            variant_conversions, variant_samples
        )

        if sig_result.get("is_significant"):
            reasons.append("statistically_significant")

        # Check if max duration reached
        if days_running >= max_days:
            reasons.append("max_duration_reached")

        # Check if sufficient sample size
        min_samples = self.calculate_sample_size(
            baseline_rate=control_conversions / control_samples if control_samples > 0 else 0.10,
            min_detectable_effect=self.min_detectable_effect,
        )

        if control_samples >= min_samples and variant_samples >= min_samples:
            reasons.append("sufficient_samples")

        # Decision
        should_stop = len(reasons) >= 2 or "statistically_significant" in reasons

        return {
            "should_stop": should_stop,
            "reasons": reasons,
            "days_running": days_running,
            "recommendation": "stop_test" if should_stop else "continue_test",
        }
