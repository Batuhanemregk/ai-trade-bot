"""
Scoring module for AiBotBS.
Contains pure functions for TA/ATR/RSI helpers and composite scoring glue.
"""

# Import all scoring components from composite_signal.py
try:
    from .composite_signal import (
        CompositeSignal,
        TechnicalBlock,
        MLBlock,
        NewsBlock,
        RiskBlock
    )
except ImportError:
    try:
        from .types import (
            CompositeSignal,
            TechnicalBlock,
            MLBlock,
            NewsBlock,
            RiskBlock
        )
    except ImportError:
        try:
            from application.scoring_service import (
                CompositeSignal,
                TechnicalBlock,
                MLBlock,
                NewsBlock,
                RiskBlock
            )
        except ImportError:
            raise ImportError(
                "Scoring components not found in scoring module. "
                "Expected to find them in scoring/composite_signal.py, "
                "scoring/types.py, or application/scoring_service.py"
            )

# Create alias for backward compatibility
CompositeScore = CompositeSignal

# Import scoring functions
try:
    from .scoring_functions import (
        ml_scorer,
        news_scorer,
        risk_scorer,
        ta_scorer
    )
except ImportError:
    # Create mock functions if not available
    def ml_scorer(*args, **kwargs): return {"score": 50.0, "rationale": "Mock ML scorer"}
    def news_scorer(*args, **kwargs): return {"score": 50.0, "rationale": "Mock news scorer"}
    def risk_scorer(*args, **kwargs): return {"score": 50.0, "rationale": "Mock risk scorer"}
    def ta_scorer(*args, **kwargs): return {"score": 50.0, "rationale": "Mock TA scorer"}

__all__ = [
    "CompositeScore", "CompositeSignal",
    "TechnicalBlock", "MLBlock", "NewsBlock", "RiskBlock",
    "ml_scorer", "news_scorer", "risk_scorer", "ta_scorer"
]
