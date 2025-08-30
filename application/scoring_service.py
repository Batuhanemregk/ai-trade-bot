"""
Scoring Service for AiBotBS.
Composes TA/ML/News results into composite scores using configurable weights.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from domain.models import SignalType


@dataclass
class AnalysisResult:
    """Result from a single analysis source."""
    source: str  # "ta", "ml", "news"
    symbol: str
    timestamp: datetime
    score: float  # 0.0 to 100.0
    signal: SignalType
    confidence: float  # 0.0 to 1.0
    rationale: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompositeScore:
    """Composite score combining multiple analysis sources."""
    id: str
    symbol: str
    timestamp: datetime
    overall_score: float  # 0.0 to 100.0
    overall_signal: SignalType
    overall_confidence: float  # 0.0 to 1.0
    grade: str  # A+, A, B, C, D

    # Individual component scores
    ta_score: float
    ml_score: float
    news_score: float

    # Component signals and confidences
    ta_signal: SignalType
    ml_signal: SignalType
    news_signal: SignalType

    ta_confidence: float
    ml_confidence: float
    news_confidence: float

    # Weighted contributions
    ta_weight: float
    ml_weight: float
    news_weight: float

    # Analysis details
    ta_rationale: str
    ml_rationale: str
    news_rationale: str

    # Composite rationale
    composite_rationale: str

    # Risk annotations (added by risk service)
    risk_notes: list[str] = field(default_factory=list)
    risk_penalties: dict[str, float] = field(default_factory=dict)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)


class ScoringService:
    """Service for composing analysis results into composite scores."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger("scoring_service")

        # Scoring configuration
        self.weights = config.get("scoring_weights", {
            "ta": 0.4,      # Technical Analysis weight
            "ml": 0.4,      # Machine Learning weight
            "news": 0.2     # News/Sentiment weight
        })

        # Signal thresholds
        self.buy_threshold = config.get("buy_threshold", 60.0)
        self.sell_threshold = config.get("sell_threshold", 40.0)
        self.confidence_threshold = config.get("confidence_threshold", 0.6)

        # Grade thresholds
        self.grade_thresholds = {
            "A+": 90.0,
            "A": 80.0,
            "B": 70.0,
            "C": 60.0,
            "D": 0.0
        }

        # Performance tracking
        self._scores_generated = 0
        self._signals_generated = 0
        self._last_score = None

        self.logger.info(f"Scoring service initialized with weights: {self.weights}")

    def compose_score(self, ta_result: AnalysisResult | None = None,
                     ml_result: AnalysisResult | None = None,
                     news_result: AnalysisResult | None = None,
                     symbol: str = "UNKNOWN") -> CompositeScore:
        """Compose a composite score from analysis results."""
        try:
            # Default values for missing results
            ta_result = ta_result or self._create_default_result("ta", symbol)
            ml_result = ml_result or self._create_default_result("ml", symbol)
            news_result = news_result or self._create_default_result("news", symbol)

            # Calculate weighted composite score
            ta_contribution = ta_result.score * self.weights["ta"]
            ml_contribution = ml_result.score * self.weights["ml"]
            news_contribution = news_result.score * self.weights["news"]

            overall_score = ta_contribution + ml_contribution + news_contribution

            # Apply bias service if available
            bias_action = "allow"
            bias_penalty = 0
            bias_reason = ""
            
            try:
                from .bias_service import create_bias_service
                
                # Create bias context from results
                bias_ctx = {
                    'indicators': {
                        'sma_20': ta_result.metadata.get('sma_20'),
                        'sma_50': ta_result.metadata.get('sma_50'),
                        'atr': ta_result.metadata.get('atr')
                    },
                    'close_price': ta_result.metadata.get('close_price'),
                    'news_score': news_result.score / 100.0,  # Normalize to 0-1
                    'news_category': news_result.metadata.get('category', ''),
                    'funding_rate': ta_result.metadata.get('funding_rate'),
                    'portfolio': {
                        'correlation': ta_result.metadata.get('correlation'),
                        'exposure': ta_result.metadata.get('exposure')
                    }
                }
                
                bias_service = create_bias_service(self.config, {})
                bias_decision = bias_service.compute_bias(symbol, bias_ctx)
                
                bias_action = bias_decision.action
                bias_penalty = bias_decision.score_penalty
                bias_reason = bias_decision.reason
                
                # Apply penalty if downgrade
                if bias_action == "downgrade" and bias_penalty > 0:
                    overall_score = max(0, overall_score - bias_penalty)
                    self.logger.info(f"bias decision: action=downgrade penalty={bias_penalty} reason={bias_reason}")
                elif bias_action == "block":
                    self.logger.info(f"bias decision: action=block penalty=0 reason={bias_reason}")
                else:
                    self.logger.info(f"bias decision: action=allow penalty=0 reason={bias_reason}")
                    
            except ImportError:
                self.logger.debug("Bias service not available, skipping bias computation")
            except Exception as e:
                self.logger.error(f"Bias computation failed: {e}")
                bias_action = "allow"
                bias_penalty = 0
                bias_reason = "bias_error"

            # Determine overall signal
            overall_signal = self._determine_signal(overall_score)

            # Calculate overall confidence (weighted average)
            overall_confidence = (
                ta_result.confidence * self.weights["ta"] +
                ml_result.confidence * self.weights["ml"] +
                news_result.confidence * self.weights["news"]
            )

            # Generate composite rationale
            composite_rationale = self._generate_composite_rationale(
                ta_result, ml_result, news_result, overall_score
            )
            
            # Add bias information to rationale if applicable
            if bias_action == "downgrade" and bias_penalty > 0:
                composite_rationale += f" [BIAS] {bias_reason} (-{bias_penalty})"
            elif bias_action == "block":
                composite_rationale += f" [BIAS] {bias_reason} (BLOCKED)"

            # Determine grade
            grade = self._calculate_grade(overall_score)

            # Create composite score
            composite_score = CompositeScore(
                id=str(uuid4()),
                symbol=symbol,
                timestamp=datetime.now(),
                overall_score=overall_score,
                overall_signal=overall_signal,
                overall_confidence=overall_confidence,
                grade=grade,

                # Component scores
                ta_score=ta_result.score,
                ml_score=ml_result.score,
                news_score=news_result.score,

                # Component signals
                ta_signal=ta_result.signal,
                ml_signal=ml_result.signal,
                news_signal=news_result.signal,

                # Component confidences
                ta_confidence=ta_result.confidence,
                ml_confidence=ml_result.confidence,
                news_confidence=news_result.confidence,

                # Weights
                ta_weight=self.weights["ta"],
                ml_weight=self.weights["ml"],
                news_weight=self.weights["news"],

                # Rationales
                ta_rationale=ta_result.rationale,
                ml_rationale=ml_result.rationale,
                news_rationale=news_result.rationale,
                composite_rationale=composite_rationale,

                # Risk annotations (empty initially)
                risk_notes=[],
                risk_penalties={},
                
                # Bias information
                metadata={
                    "bias_action": bias_action,
                    "bias_penalty": bias_penalty,
                    "bias_reason": bias_reason
                }
            )

            self._scores_generated += 1
            self._last_score = composite_score

            self.logger.info(f"Generated composite score for {symbol}: {grade} ({overall_score:.2f})")
            return composite_score

        except Exception as e:
            self.logger.error(f"Error composing score for {symbol}: {e}")
            raise

    def _create_default_result(self, source: str, symbol: str) -> AnalysisResult:
        """Create a default analysis result when source data is missing."""
        return AnalysisResult(
            source=source,
            symbol=symbol,
            timestamp=datetime.now(),
            score=50.0,  # Neutral score
            signal=SignalType.HOLD,
            confidence=0.0,  # No confidence in default result
            rationale=f"No {source.upper()} data available for {symbol}",
            metadata={"default": True, "reason": "missing_data"}
        )

    def _determine_signal(self, score: float) -> SignalType:
        """Determine signal based on score thresholds."""
        if score >= self.buy_threshold:
            return SignalType.BUY
        elif score <= self.sell_threshold:
            return SignalType.SELL
        else:
            return SignalType.HOLD

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade based on score."""
        for grade, threshold in self.grade_thresholds.items():
            if score >= threshold:
                return grade
        return "D"

    def _generate_composite_rationale(self, ta_result: AnalysisResult,
                                    ml_result: AnalysisResult,
                                    news_result: AnalysisResult,
                                    overall_score: float) -> str:
        """Generate composite rationale explaining the overall score."""
        rationale_parts = []

        # Add overall assessment
        if overall_score >= 80:
            rationale_parts.append("Strong bullish signals across multiple timeframes")
        elif overall_score >= 60:
            rationale_parts.append("Moderate bullish signals with some caution")
        elif overall_score >= 40:
            rationale_parts.append("Mixed signals with bearish bias")
        else:
            rationale_parts.append("Strong bearish signals across multiple timeframes")

        # Add component highlights
        if ta_result.score >= 70:
            rationale_parts.append(f"Strong technical analysis ({ta_result.score:.1f})")
        elif ta_result.score <= 30:
            rationale_parts.append(f"Weak technical analysis ({ta_result.score:.1f})")

        if ml_result.score >= 70:
            rationale_parts.append(f"Strong ML prediction ({ml_result.score:.1f})")
        elif ml_result.score <= 30:
            rationale_parts.append(f"Weak ML prediction ({ml_result.score:.1f})")

        if news_result.score >= 0.5:
            rationale_parts.append(f"Positive news sentiment ({news_result.score:.2f})")
        elif news_result.score <= -0.5:
            rationale_parts.append(f"Negative news sentiment ({news_result.score:.2f})")

        return ". ".join(rationale_parts) + "."

    def get_score_summary(self, symbol: str) -> dict[str, Any]:
        """Get a summary of the latest score for a symbol."""
        if not self._last_score or self._last_score.symbol != symbol:
            return {"error": "No score available for symbol"}

        score = self._last_score
        return {
            "symbol": score.symbol,
            "grade": score.grade,
            "overall_score": score.overall_score,
            "signal": score.overall_signal.value,
            "confidence": score.overall_confidence,
            "rationale": score.composite_rationale,
            "components": {
                "ta": {"score": score.ta_score, "signal": score.ta_signal.value, "confidence": score.ta_confidence},
                "ml": {"score": score.ml_score, "signal": score.ml_signal.value, "confidence": score.ml_confidence},
                "news": {"score": score.news_score, "signal": score.news_signal.value, "confidence": score.news_confidence}
            },
            "weights": self.weights,
            "risk_notes": score.risk_notes,
            "risk_penalties": score.risk_penalties
        }

    def get_service_status(self) -> dict[str, Any]:
        """Get service status and performance metrics."""
        return {
            "weights": self.weights,
            "thresholds": {
                "buy": self.buy_threshold,
                "sell": self.sell_threshold,
                "confidence": self.confidence_threshold
            },
            "grade_thresholds": self.grade_thresholds,
            "performance": {
                "scores_generated": self._scores_generated,
                "signals_generated": self._signals_generated,
                "last_score": self._last_score.symbol if self._last_score else None
            }
        }
