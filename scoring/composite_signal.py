"""
Composite Signal Model - Unified scoring system for trading signals
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Optional

from loguru import logger


@dataclass
class TechnicalBlock:
    """Technical analysis scoring block."""
    score: float  # 0-100
    rationale: str
    flags: dict[str, Any]  # trend, meanrev, breakout, dir_hint


@dataclass
class MLBlock:
    """Machine learning scoring block."""
    score: float | None  # 0-100 or None for TA-only mode
    rationale: str
    details: dict[str, Any]


@dataclass
class NewsBlock:
    """News sentiment scoring block."""
    score: float | None  # 0-100 or None (skip weight)
    categories: list[str]
    rationale: str
    volatility_impact: float  # 0-1


@dataclass
class RiskBlock:
    """Risk management scoring block."""
    score: float  # 0-100
    details: dict[str, Any]


@dataclass
class CompositeSignal:
    """Unified composite trading signal with final scoring."""

    # Basic identification
    symbol: str
    timestamp: datetime
    timeframes: dict[str, str]

    # Scoring blocks
    technical: TechnicalBlock
    ml: MLBlock
    news: NewsBlock
    risk: RiskBlock

    # Final computed values (set by finalize())
    final_score: float = 0.0
    decision: Literal["LONG", "SHORT", "FLAT"] = "FLAT"
    confidence_pct: float = 0.0
    grade: Literal["A+", "A", "B", "C", "D"] = "D"

    # Metadata
    meta: dict[str, Any] = None

    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.meta is None:
            self.meta = {}

    def finalize(self, weights: dict[str, float], thresholds: dict[str, Any],
                 direction_hint: str | None = None, ml_boost_config: dict | None = None) -> None:
        """
        Compute final score and decision based on weighted components.
        
        Args:
            weights: Dictionary with keys 'technical', 'ml', 'news', 'risk'
            thresholds: Dictionary with grading thresholds and min confidence
            direction_hint: Optional direction hint from technical analysis
            ml_boost_config: Optional ML boost configuration with 'enabled' and 'tiers'
        """
        try:
            # Calculate weighted final score, handling None values (skip weight)
            news_score = self.news.score if self.news.score is not None else 50.0
            risk_score = self.risk.score if self.risk.score is not None else 50.0
            ml_score = self.ml.score if self.ml.score is not None else 50.0
            ta_score = self.technical.score
            
            # Apply ML boost based on TA score thresholds
            ml_boost_multiplier = 1.0
            if ml_boost_config and ml_boost_config.get('enabled', False) and self.ml.score is not None:
                tiers = ml_boost_config.get('tiers', [])
                # Sort tiers by ta_threshold descending to find highest matching
                sorted_tiers = sorted(tiers, key=lambda x: x.get('ta_threshold', 0), reverse=True)
                for tier in sorted_tiers:
                    if ta_score >= tier.get('ta_threshold', 100):
                        ml_boost_multiplier = tier.get('multiplier', 1.0)
                        break
                
                if ml_boost_multiplier > 1.0:
                    original_ml = ml_score
                    ml_score = min(100.0, ml_score * ml_boost_multiplier)  # Cap at 100
                    logger.info(f"[COMPOSITE] ML Boost: TA={ta_score:.1f} >= threshold → ML {original_ml:.1f} × {ml_boost_multiplier} = {ml_score:.1f}")
            
            # Recalculate weights if any component is None (redistribute weight)
            adjusted_weights = weights.copy()
            total_weight = sum(adjusted_weights.values())
            
            # ML redistribution (for TA-only mode) - redistribute ML weight to TA
            if self.ml.score is None:
                ml_weight = adjusted_weights.pop('ml', 0.0)
                ta_weight = adjusted_weights.get('technical', 0.0)
                adjusted_weights['technical'] = ta_weight + ml_weight  # ML weight goes to TA
                total_weight = sum(adjusted_weights.values())
                ml_score = 50.0  # Neutral for calculation (won't affect score since weight is 0)
                logger.info(f"[COMPOSITE] TA-only mode: ML weight ({ml_weight:.2f}) redistributed to TA")
            
            if self.news.score is None:
                # Redistribute news weight to other components
                news_weight = adjusted_weights.pop('news', 0.0)
                if total_weight > 0:
                    scale = total_weight / (total_weight - news_weight) if (total_weight - news_weight) > 0 else 1.0
                    adjusted_weights = {k: v * scale for k, v in adjusted_weights.items()}
                news_score = 50.0  # Neutral for calculation
            
            if self.risk.score is None:
                # Redistribute risk weight to other components
                risk_weight = adjusted_weights.pop('risk', 0.0)
                total_weight = sum(adjusted_weights.values())
                if total_weight > 0:
                    scale = total_weight / (total_weight - risk_weight) if (total_weight - risk_weight) > 0 else 1.0
                    adjusted_weights = {k: v * scale for k, v in adjusted_weights.items()}
                risk_score = 50.0  # Neutral for calculation
            
            self.final_score = (
                adjusted_weights.get('technical', 0.0) * self.technical.score +
                adjusted_weights.get('ml', 0.0) * ml_score +
                adjusted_weights.get('news', 0.0) * news_score +
                adjusted_weights.get('risk', 0.0) * risk_score
            )

            # Ensure score is within bounds
            self.final_score = max(0.0, min(100.0, self.final_score))
            
            # Log weight adjustment if any component was None
            if self.news.score is None or self.risk.score is None:
                logger.debug(f"[COMPOSITE] Adjusted weights: {adjusted_weights} (news/risk skipped)")

            # Set confidence percentage
            self.confidence_pct = self.final_score

            # Determine grade based on thresholds
            grade_thresholds = thresholds.get('grades', {})

            # Handle both list and single value formats
            def get_threshold(grade_key, default_value):
                threshold = grade_thresholds.get(grade_key, default_value)
                if isinstance(threshold, list):
                    return threshold[0]  # Use first value from list
                return threshold  # Use single value directly

            if self.final_score >= get_threshold('A+', 90):
                self.grade = "A+"
            elif self.final_score >= get_threshold('A', 80):
                self.grade = "A"
            elif self.final_score >= get_threshold('B', 70):
                self.grade = "B"
            elif self.final_score >= get_threshold('C', 60):
                self.grade = "C"
            else:
                self.grade = "D"

            # Determine decision based on confidence and direction consensus
            min_confidence = thresholds.get('min_confidence_pct', 50)  # Final score eşiği: 50

            if self.confidence_pct < min_confidence:
                self.decision = "FLAT"
            else:
                # Use direction hint if available, otherwise determine from technical+ML consensus
                if direction_hint and direction_hint in ["LONG", "SHORT"]:
                    self.decision = direction_hint
                else:
                    # Determine from technical and ML consensus
                    tech_direction = self.technical.flags.get("dir_hint", "FLAT")
                    ml_direction = self._get_ml_direction()

                    if tech_direction == ml_direction and tech_direction != "FLAT":
                        self.decision = tech_direction
                    elif tech_direction != "FLAT":
                        self.decision = tech_direction
                    elif ml_direction != "FLAT":
                        self.decision = ml_direction
                    else:
                        self.decision = "FLAT"

            # Add strategy metadata
            self._add_strategy_metadata()

            logger.info(f"✅ CompositeSignal finalized for {self.symbol}: "
                       f"Score={self.final_score:.1f}, Decision={self.decision}, Grade={self.grade}")

        except Exception as e:
            logger.error(f"❌ Error finalizing CompositeSignal for {self.symbol}: {e}")
            # Set safe defaults
            self.final_score = 0.0
            self.decision = "FLAT"
            self.confidence_pct = 0.0
            self.grade = "D"

    def _get_ml_direction(self) -> str:
        """Extract direction hint from ML block."""
        ml_score = self.ml.score
        if ml_score is None:
            return "FLAT"  # TA-only mode - no ML direction hint
        if ml_score >= 60:  # ML direction eşiği: 60 (70'ten düşürüldü)
            return "LONG"
        elif ml_score <= 40:  # ML direction eşiği: 40 (30'dan yükseltildi)
            return "SHORT"
        else:
            return "FLAT"

    def _add_strategy_metadata(self):
        """Add strategy-specific metadata like SL/TP suggestions."""
        strategy_flags = self.technical.flags

        # Add strategy metadata
        if strategy_flags.get("trend") == "up":
            self.meta["strategy"] = "trend_following"
            self.meta["sl_pct"] = 2.0
            self.meta["tp_pct"] = 4.0
        elif strategy_flags.get("meanrev") == "on":
            self.meta["strategy"] = "mean_reversion"
            self.meta["sl_pct"] = 1.5
            self.meta["tp_pct"] = 3.0
        elif strategy_flags.get("breakout") == "on":
            self.meta["strategy"] = "breakout"
            self.meta["sl_pct"] = 2.5
            self.meta["tp_pct"] = 5.0
        else:
            self.meta["strategy"] = "mixed"
            self.meta["sl_pct"] = 2.0
            self.meta["tp_pct"] = 4.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "timeframes": self.timeframes,
            "technical": {
                "score": self.technical.score,
                "rationale": self.technical.rationale,
                "flags": self.technical.flags
            },
            "ml": {
                "score": self.ml.score,
                "rationale": self.ml.rationale,
                "details": self.ml.details
            },
            "news": {
                "score": self.news.score,
                "categories": self.news.categories,
                "rationale": self.news.rationale,
                "volatility_impact": self.news.volatility_impact
            },
            "risk": {
                "score": self.risk.score,
                "details": self.risk.details
            },
            "final_score": self.final_score,
            "decision": self.decision,
            "confidence_pct": self.confidence_pct,
            "grade": self.grade,
            "meta": self.meta
        }

    def get_position_size_multiplier(self) -> float:
        """Get position size multiplier based on grade."""
        grade_multipliers = {
            "A+": 1.0,  # Large position
            "A": 0.7,   # Medium position
            "B": 0.5,   # Small position
            "C": 0.3,   # Tiny position
            "D": 0.0    # No trade
        }
        return grade_multipliers.get(self.grade, 0.0)

    def is_tradeable(self) -> bool:
        """Check if signal is tradeable based on confidence."""
        return self.confidence_pct >= 60 and self.decision != "FLAT"

    def get_summary(self) -> str:
        """Get human-readable summary of the signal."""
        ml_display = f"{self.ml.score:.0f}" if self.ml.score is not None else "N/A"
        news_display = f"{self.news.score:.0f}" if self.news.score is not None else "50"
        risk_display = f"{self.risk.score:.0f}" if self.risk.score is not None else "50"
        return (f"{self.symbol}: {self.decision} | "
                f"Score: {self.final_score:.1f}/100 ({self.grade}) | "
                f"TA:{self.technical.score:.0f} ML:{ml_display} "
                f"News:{news_display} Risk:{risk_display}")
