"""
Strategy Pattern - Domain layer strategy interfaces and base classes.
Follows SOLID principles and Clean Architecture patterns.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass
from enum import Enum


class StrategyType(Enum):
    """Strategy types enumeration."""
    TECHNICAL_ANALYSIS = "technical_analysis"
    MACHINE_LEARNING = "machine_learning"
    NEWS_SENTIMENT = "news_sentiment"
    COMPOSITE = "composite"
    RISK_MANAGEMENT = "risk_management"
    POSITION_SIZING = "position_sizing"
    ENTRY_EXIT = "entry_exit"


class StrategyStatus(Enum):
    """Strategy status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    DEPRECATED = "deprecated"
    ERROR = "error"


@dataclass
class StrategyContext:
    """Context data for strategy execution."""
    symbol: str
    timeframe: str
    market_data: Dict[str, Any]
    portfolio_state: Optional[Dict[str, Any]] = None
    risk_parameters: Optional[Dict[str, Any]] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class StrategyResult:
    """Result of strategy execution."""
    success: bool
    score: float
    confidence: float
    signal: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: datetime = None
    execution_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class AnalysisStrategy(ABC):
    """
    Abstract base class for analysis strategies.
    
    This follows the Strategy Pattern and Single Responsibility Principle.
    Each strategy is responsible for one type of analysis.
    """
    
    def __init__(self, name: str, strategy_type: StrategyType):
        self.name = name
        self.strategy_type = strategy_type
        self.status = StrategyStatus.ACTIVE
        self.version = "1.0.0"
        self.created_at = datetime.now()
        self.last_execution = None
        self.execution_count = 0
        self.success_count = 0
        self.error_count = 0
    
    @abstractmethod
    async def analyze(self, context: StrategyContext) -> StrategyResult:
        """
        Execute the strategy analysis.
        
        Args:
            context: Strategy execution context
            
        Returns:
            StrategyResult with analysis outcome
        """
        pass
    
    @abstractmethod
    def validate_context(self, context: StrategyContext) -> bool:
        """
        Validate that the context contains required data.
        
        Args:
            context: Strategy execution context
            
        Returns:
            True if context is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def get_required_data(self) -> List[str]:
        """
        Get list of required data keys for this strategy.
        
        Returns:
            List of required data keys
        """
        pass
    
    def can_execute(self, context: StrategyContext) -> bool:
        """
        Check if strategy can execute with given context.
        
        Args:
            context: Strategy execution context
            
        Returns:
            True if strategy can execute, False otherwise
        """
        if self.status != StrategyStatus.ACTIVE:
            return False
        
        return self.validate_context(context)
    
    def update_metrics(self, result: StrategyResult):
        """Update strategy execution metrics."""
        self.last_execution = datetime.now()
        self.execution_count += 1
        
        if result.success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_success_rate(self) -> float:
        """Get strategy success rate."""
        if self.execution_count == 0:
            return 0.0
        return self.success_count / self.execution_count
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get strategy metrics."""
        return {
            "name": self.name,
            "type": self.strategy_type.value,
            "status": self.status.value,
            "version": self.version,
            "created_at": self.created_at,
            "last_execution": self.last_execution,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.get_success_rate()
        }


class TechnicalAnalysisStrategy(AnalysisStrategy):
    """Technical analysis strategy base class."""
    
    def __init__(self, name: str):
        super().__init__(name, StrategyType.TECHNICAL_ANALYSIS)
        self.indicators = []
        self.timeframes = []
    
    def get_required_data(self) -> List[str]:
        """Get required data for technical analysis."""
        return ["ohlcv", "ticker"]
    
    def validate_context(self, context: StrategyContext) -> bool:
        """Validate technical analysis context."""
        if not context.market_data:
            return False
        
        required_data = self.get_required_data()
        for key in required_data:
            if key not in context.market_data:
                return False
        
        return True
    
    def analyze(self, context: StrategyContext) -> StrategyResult:
        """Analyze market data using technical indicators."""
        if not self.validate_context(context):
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                score=0.0,
                confidence=0.0,
                signals=[],
                metadata={"error": "Invalid context"}
            )
        
        # Mock analysis for now
        return StrategyResult(
            strategy_name=self.name,
            success=True,
            score=0.7,
            confidence=0.8,
            signals=["RSI oversold", "MACD bullish crossover"],
            metadata={"indicators": self.indicators, "timeframes": self.timeframes}
        )


class MachineLearningStrategy(AnalysisStrategy):
    """Machine learning strategy base class."""
    
    def __init__(self, name: str):
        super().__init__(name, StrategyType.MACHINE_LEARNING)
        self.model_version = "1.0.0"
        self.feature_columns = []
        self.prediction_horizon = 1
    
    def get_required_data(self) -> List[str]:
        """Get required data for ML strategy."""
        return ["ohlcv", "features", "model"]
    
    def validate_context(self, context: StrategyContext) -> bool:
        """Validate ML strategy context."""
        if not context.market_data:
            return False
        
        required_data = self.get_required_data()
        for key in required_data:
            if key not in context.market_data:
                return False
        
        return True
    
    def analyze(self, context: StrategyContext) -> StrategyResult:
        """Analyze market data using machine learning model."""
        if not self.validate_context(context):
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                score=0.0,
                confidence=0.0,
                signals=[],
                metadata={"error": "Invalid context"}
            )
        
        # Mock ML analysis for now
        return StrategyResult(
            strategy_name=self.name,
            success=True,
            score=0.8,
            confidence=0.9,
            signals=["ML prediction: bullish", "Confidence: high"],
            metadata={"model_version": self.model_version, "features": self.feature_columns}
        )


class NewsSentimentStrategy(AnalysisStrategy):
    """News sentiment analysis strategy base class."""
    
    def __init__(self, name: str):
        super().__init__(name, StrategyType.NEWS_SENTIMENT)
        self.sentiment_threshold = 0.5
        self.news_sources = []
        self.analysis_window_hours = 24
    
    def get_required_data(self) -> List[str]:
        """Get required data for news sentiment strategy."""
        return ["news_data", "sentiment_scores"]
    
    def validate_context(self, context: StrategyContext) -> bool:
        """Validate news sentiment strategy context."""
        if not context.market_data:
            return False
        
        required_data = self.get_required_data()
        for key in required_data:
            if key not in context.market_data:
                return False
        
        return True
    
    def analyze(self, context: StrategyContext) -> StrategyResult:
        """Analyze news sentiment data."""
        if not self.validate_context(context):
            return StrategyResult(
                strategy_name=self.name,
                success=False,
                score=0.0,
                confidence=0.0,
                signals=[],
                metadata={"error": "Invalid context"}
            )
        
        # Mock sentiment analysis for now
        return StrategyResult(
            strategy_name=self.name,
            success=True,
            score=0.6,
            confidence=0.7,
            signals=["Sentiment: neutral", "News impact: low"],
            metadata={"sources": self.news_sources, "window_hours": self.analysis_window_hours}
        )


class CompositeStrategy(AnalysisStrategy):
    """
    Composite strategy that combines multiple strategies.
    
    This follows the Composite Pattern and allows for complex
    strategy combinations while maintaining the same interface.
    """
    
    def __init__(self, name: str):
        super().__init__(name, StrategyType.COMPOSITE)
        self.strategies: List[AnalysisStrategy] = []
        self.weights: Dict[str, float] = {}
        self.combination_method = "weighted_average"
    
    def add_strategy(self, strategy: AnalysisStrategy, weight: float = 1.0):
        """Add a strategy to the composite."""
        self.strategies.append(strategy)
        self.weights[strategy.name] = weight
    
    def remove_strategy(self, strategy_name: str):
        """Remove a strategy from the composite."""
        self.strategies = [s for s in self.strategies if s.name != strategy_name]
        if strategy_name in self.weights:
            del self.weights[strategy_name]
    
    def get_required_data(self) -> List[str]:
        """Get required data from all strategies."""
        required_data = set()
        for strategy in self.strategies:
            required_data.update(strategy.get_required_data())
        return list(required_data)
    
    def validate_context(self, context: StrategyContext) -> bool:
        """Validate context for all strategies."""
        for strategy in self.strategies:
            if not strategy.can_execute(context):
                return False
        return True
    
    async def analyze(self, context: StrategyContext) -> StrategyResult:
        """Execute composite strategy analysis."""
        if not self.can_execute(context):
            return StrategyResult(
                success=False,
                score=0.0,
                confidence=0.0,
                error_message="Composite strategy cannot execute"
            )
        
        try:
            # Execute all strategies
            results = []
            for strategy in self.strategies:
                result = await strategy.analyze(context)
                results.append(result)
                strategy.update_metrics(result)
            
            # Combine results based on method
            if self.combination_method == "weighted_average":
                final_result = self._combine_weighted_average(results)
            elif self.combination_method == "majority_vote":
                final_result = self._combine_majority_vote(results)
            else:
                final_result = self._combine_weighted_average(results)
            
            # Update composite metrics
            self.update_metrics(final_result)
            
            return final_result
            
        except Exception as e:
            return StrategyResult(
                success=False,
                score=0.0,
                confidence=0.0,
                error_message=f"Composite strategy failed: {str(e)}"
            )
    
    def _combine_weighted_average(self, results: List[StrategyResult]) -> StrategyResult:
        """Combine results using weighted average."""
        if not results:
            return StrategyResult(
                success=False,
                score=0.0,
                confidence=0.0,
                error_message="No results to combine"
            )
        
        total_weight = 0
        weighted_score = 0
        weighted_confidence = 0
        success_count = 0
        
        for result in results:
            if result.success:
                weight = self.weights.get(result.name, 1.0)
                total_weight += weight
                weighted_score += result.score * weight
                weighted_confidence += result.confidence * weight
                success_count += 1
        
        if total_weight == 0:
            return StrategyResult(
                success=False,
                score=0.0,
                confidence=0.0,
                error_message="No successful results"
            )
        
        final_score = weighted_score / total_weight
        final_confidence = weighted_confidence / total_weight
        
        return StrategyResult(
            success=True,
            score=final_score,
            confidence=final_confidence,
            metadata={
                "combination_method": "weighted_average",
                "strategy_count": len(results),
                "successful_strategies": success_count,
                "individual_results": [r.get_metrics() for r in results]
            }
        )
    
    def _combine_majority_vote(self, results: List[StrategyResult]) -> StrategyResult:
        """Combine results using majority vote."""
        if not results:
            return StrategyResult(
                success=False,
                score=0.0,
                confidence=0.0,
                error_message="No results to combine"
            )
        
        # Count signals
        signal_counts = {}
        total_confidence = 0
        success_count = 0
        
        for result in results:
            if result.success:
                signal = result.signal or "hold"
                signal_counts[signal] = signal_counts.get(signal, 0) + 1
                total_confidence += result.confidence
                success_count += 1
        
        if success_count == 0:
            return StrategyResult(
                success=False,
                score=0.0,
                confidence=0.0,
                error_message="No successful results"
            )
        
        # Find majority signal
        majority_signal = max(signal_counts.items(), key=lambda x: x[1])[0]
        final_confidence = total_confidence / success_count
        
        return StrategyResult(
            success=True,
            score=0.5 if majority_signal == "hold" else 0.8,
            confidence=final_confidence,
            signal=majority_signal,
            metadata={
                "combination_method": "majority_vote",
                "strategy_count": len(results),
                "successful_strategies": success_count,
                "signal_counts": signal_counts,
                "majority_signal": majority_signal
            }
        )


class StrategyRegistry:
    """
    Registry for managing strategies.
    
    This follows the Registry Pattern and allows for dynamic
    strategy registration and retrieval.
    """
    
    def __init__(self):
        self.strategies: Dict[str, AnalysisStrategy] = {}
        self.strategy_types: Dict[StrategyType, List[str]] = {}
    
    def register(self, strategy: AnalysisStrategy) -> bool:
        """Register a strategy."""
        try:
            self.strategies[strategy.name] = strategy
            
            # Add to type index
            if strategy.strategy_type not in self.strategy_types:
                self.strategy_types[strategy.strategy_type] = []
            self.strategy_types[strategy.strategy_type].append(strategy.name)
            
            return True
        except Exception:
            return False
    
    def unregister(self, strategy_name: str) -> bool:
        """Unregister a strategy."""
        try:
            if strategy_name in self.strategies:
                strategy = self.strategies[strategy_name]
                
                # Remove from type index
                if strategy.strategy_type in self.strategy_types:
                    self.strategy_types[strategy.strategy_type] = [
                        name for name in self.strategy_types[strategy.strategy_type]
                        if name != strategy_name
                    ]
                
                del self.strategies[strategy_name]
                return True
            
            return False
        except Exception:
            return False
    
    def get_strategy(self, name: str) -> Optional[AnalysisStrategy]:
        """Get a strategy by name."""
        return self.strategies.get(name)
    
    def get_strategies_by_type(self, strategy_type: StrategyType) -> List[AnalysisStrategy]:
        """Get all strategies of a specific type."""
        strategy_names = self.strategy_types.get(strategy_type, [])
        return [self.strategies[name] for name in strategy_names if name in self.strategies]
    
    def get_all_strategies(self) -> List[AnalysisStrategy]:
        """Get all registered strategies."""
        return list(self.strategies.values())
    
    def get_strategy_names(self) -> List[str]:
        """Get names of all registered strategies."""
        return list(self.strategies.keys())
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        return {
            "total_strategies": len(self.strategies),
            "strategies_by_type": {
                strategy_type.value: len(strategies)
                for strategy_type, strategies in self.strategy_types.items()
            },
            "strategy_names": self.get_strategy_names(),
            "active_strategies": len([s for s in self.strategies.values() if s.status == StrategyStatus.ACTIVE])
        }
