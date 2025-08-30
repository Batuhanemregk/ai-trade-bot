"""
Technical Analysis Agent for AiBotBS.
Performs technical analysis using various indicators and patterns.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd

from domain.errors import AgentError
from domain.models import SignalType

from ..core.base import BaseAgent, Message, MessageType
from ..core.tools import Tool, ToolCategory


@dataclass
class TechnicalIndicator:
    """Technical indicator result."""
    name: str
    value: float
    signal: str  # "buy", "sell", "hold"
    strength: float  # 0.0 to 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TechnicalAnalysis:
    """Complete technical analysis result."""
    symbol: str
    timeframe: str
    timestamp: datetime
    indicators: dict[str, TechnicalIndicator]
    overall_signal: SignalType
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


class TechnicalAnalysisAgent(BaseAgent):
    """Technical analysis agent that performs various indicators."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "ta_agent", config)

        # Analysis configuration
        self._indicators = config.get("indicators", ["rsi", "macd", "bb", "atr", "sma"])
        self._timeframes = config.get("timeframes", ["1h", "4h", "1d"])
        self._warmup_periods = config.get("warmup_periods", 100)
        self._signal_thresholds = config.get("signal_thresholds", {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "macd_signal": 0.0,
            "bb_std_dev": 2.0
        })

        # Performance tracking
        self._analysis_count = 0
        self._signal_count = 0
        self._last_analysis = None

        # Register message handlers
        self._register_message_handlers()

        # Register tools
        self._register_tools()

    async def _initialize(self) -> None:
        """Initialize the TA agent."""
        self.logger.info("Initializing technical analysis agent")

        # Validate configuration
        self._validate_config()

        # Start analysis processor
        asyncio.create_task(self._analysis_processor())

        self.logger.info("Technical analysis agent initialized")

    async def _cleanup(self) -> None:
        """Cleanup when stopping the agent."""
        self.logger.info("Cleaning up technical analysis agent")
        self.logger.info("Technical analysis agent cleanup completed")

    def _register_message_handlers(self) -> None:
        """Register message handlers."""
        self.register_message_handler(MessageType.TASK, self._handle_task_message)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

    def _register_tools(self) -> None:
        """Register TA-specific tools."""
        from ..core.tools import get_tool_registry

        registry = get_tool_registry()
        registry.register_tool(TechnicalAnalysisTool(self), ToolCategory.ANALYSIS)
        registry.register_tool(IndicatorCalculationTool(self), ToolCategory.ANALYSIS)

    def _validate_config(self) -> None:
        """Validate agent configuration."""
        required_indicators = ["rsi", "macd", "bb", "atr", "sma"]
        for indicator in required_indicators:
            if indicator not in self._indicators:
                self.logger.warning(f"Missing required indicator: {indicator}")

        if self._warmup_periods < 50:
            self.logger.warning("Warmup periods too low, may cause unreliable signals")

    async def _analysis_processor(self) -> None:
        """Process analysis requests."""
        while self._running:
            try:
                # Process any pending analysis requests
                await asyncio.sleep(1)
            except Exception as e:
                self.logger.error(f"Error in analysis processor: {e}")
                await asyncio.sleep(5)

    async def _handle_task_message(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "technical_analysis":
                result = await self._perform_technical_analysis(message.body)

                # Send result back
                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="technical_analysis_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            elif task_type == "indicator_calculation":
                result = await self._calculate_indicator(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="indicator_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            else:
                self.logger.warning(f"Unknown task type: {task_type}")

        except Exception as e:
            self.logger.error(f"Error handling task message: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="task_error",
                body={"error": str(e)},
                reply_to=message.id
            )
            await self.send_message(error_response)

    async def _handle_data_update(self, message: Message) -> None:
        """Handle data update messages."""
        # Process market data updates
        data_type = message.body.get("data_type")
        if data_type == "ohlcv":
            await self._process_market_data(message.body)

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        command = message.body.get("command")
        parameters = message.body.get("parameters", {})

        try:
            if command == "get_status":
                result = self.get_status()
            elif command == "get_indicators":
                result = {"indicators": self._indicators}
            elif command == "get_config":
                result = {
                    "indicators": self._indicators,
                    "timeframes": self._timeframes,
                    "warmup_periods": self._warmup_periods,
                    "signal_thresholds": self._signal_thresholds
                }
            else:
                result = {"error": f"Unknown command: {command}"}

            response = Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject=f"command_response_{command}",
                body=result,
                reply_to=message.id
            )
            await self.send_message(response)

        except Exception as e:
            self.logger.error(f"Error handling command: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="command_error",
                body={"error": str(e)},
                reply_to=message.id
            )
            await self.send_message(error_response)

    async def _perform_technical_analysis(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Perform complete technical analysis."""
        try:
            symbol = parameters.get("symbol")
            timeframe = parameters.get("timeframe", "1h")
            ohlcv_data = parameters.get("ohlcv_data")

            if not symbol or not ohlcv_data:
                raise AgentError("Missing required parameters: symbol or ohlcv_data")

            # Convert to DataFrame
            df = pd.DataFrame(ohlcv_data)
            if len(df) < self._warmup_periods:
                raise AgentError(f"Insufficient data: {len(df)} < {self._warmup_periods}")

            # Calculate indicators
            indicators = {}
            for indicator_name in self._indicators:
                indicator = await self._calculate_indicator_value(indicator_name, df)
                indicators[indicator_name] = indicator

            # Determine overall signal
            overall_signal, confidence = self._determine_overall_signal(indicators)

            # Create analysis result
            analysis = TechnicalAnalysis(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.utcnow(),
                indicators=indicators,
                overall_signal=overall_signal,
                confidence=confidence
            )

            # Update statistics
            self._analysis_count += 1
            if overall_signal != SignalType.HOLD:
                self._signal_count += 1
            self._last_analysis = analysis

            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "overall_signal": overall_signal.value,
                "confidence": confidence,
                "indicators": {
                    name: {
                        "value": ind.value,
                        "signal": ind.signal,
                        "strength": ind.strength
                    }
                    for name, ind in indicators.items()
                },
                "timestamp": analysis.timestamp.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Technical analysis failed: {e}")
            raise AgentError(f"Technical analysis failed: {e}")

    async def _calculate_indicator(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Calculate a specific indicator."""
        try:
            indicator_name = parameters.get("indicator_name")
            ohlcv_data = parameters.get("ohlcv_data")

            if not indicator_name or not ohlcv_data:
                raise AgentError("Missing required parameters: indicator_name or ohlcv_data")

            df = pd.DataFrame(ohlcv_data)
            if len(df) < self._warmup_periods:
                raise AgentError(f"Insufficient data: {len(df)} < {self._warmup_periods}")

            indicator = await self._calculate_indicator_value(indicator_name, df)

            return {
                "indicator_name": indicator_name,
                "value": indicator.value,
                "signal": indicator.signal,
                "strength": indicator.strength,
                "timestamp": indicator.timestamp.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Indicator calculation failed: {e}")
            raise AgentError(f"Indicator calculation failed: {e}")

    async def _calculate_indicator_value(self, indicator_name: str, df: pd.DataFrame) -> TechnicalIndicator:
        """Calculate a specific indicator value."""
        if indicator_name == "rsi":
            return self._calculate_rsi(df)
        elif indicator_name == "macd":
            return self._calculate_macd(df)
        elif indicator_name == "bb":
            return self._calculate_bollinger_bands(df)
        elif indicator_name == "atr":
            return self._calculate_atr(df)
        elif indicator_name == "sma":
            return self._calculate_sma(df)
        else:
            raise AgentError(f"Unknown indicator: {indicator_name}")

    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> TechnicalIndicator:
        """Calculate RSI indicator."""
        try:
            # Calculate price changes
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            # Calculate RSI
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            current_rsi = rsi.iloc[-1]

            # Determine signal
            if current_rsi < self._signal_thresholds["rsi_oversold"]:
                signal = "buy"
                strength = (self._signal_thresholds["rsi_oversold"] - current_rsi) / self._signal_thresholds["rsi_oversold"]
            elif current_rsi > self._signal_thresholds["rsi_overbought"]:
                signal = "sell"
                strength = (current_rsi - self._signal_thresholds["rsi_overbought"]) / (100 - self._signal_thresholds["rsi_overbought"])
            else:
                signal = "hold"
                strength = 0.0

            return TechnicalIndicator(
                name="rsi",
                value=float(current_rsi),
                signal=signal,
                strength=min(strength, 1.0)
            )

        except Exception as e:
            self.logger.error(f"RSI calculation failed: {e}")
            return TechnicalIndicator(
                name="rsi",
                value=50.0,
                signal="hold",
                strength=0.0
            )

    def _calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> TechnicalIndicator:
        """Calculate MACD indicator."""
        try:
            # Calculate EMAs
            ema_fast = df['close'].ewm(span=fast).mean()
            ema_slow = df['close'].ewm(span=slow).mean()

            # Calculate MACD line and signal line
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal).mean()

            current_macd = macd_line.iloc[-1]
            current_signal = signal_line.iloc[-1]

            # Determine signal
            if current_macd > current_signal:
                signal_type = "buy"
                strength = min(abs(current_macd - current_signal) / abs(current_macd), 1.0) if current_macd != 0 else 0.0
            elif current_macd < current_signal:
                signal_type = "sell"
                strength = min(abs(current_macd - current_signal) / abs(current_macd), 1.0) if current_macd != 0 else 0.0
            else:
                signal_type = "hold"
                strength = 0.0

            return TechnicalIndicator(
                name="macd",
                value=float(current_macd),
                signal=signal_type,
                strength=strength
            )

        except Exception as e:
            self.logger.error(f"MACD calculation failed: {e}")
            return TechnicalIndicator(
                name="macd",
                value=0.0,
                signal="hold",
                strength=0.0
            )

    def _calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20) -> TechnicalIndicator:
        """Calculate Bollinger Bands indicator."""
        try:
            # Calculate SMA and standard deviation
            sma = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()

            # Calculate bands
            upper_band = sma + (std * self._signal_thresholds["bb_std_dev"])
            lower_band = sma - (std * self._signal_thresholds["bb_std_dev"])

            current_price = df['close'].iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_sma = sma.iloc[-1]

            # Determine signal
            if current_price < current_lower:
                signal = "buy"
                strength = min((current_lower - current_price) / (current_sma - current_lower), 1.0)
            elif current_price > current_upper:
                signal = "sell"
                strength = min((current_price - current_upper) / (current_upper - current_sma), 1.0)
            else:
                signal = "hold"
                strength = 0.0

            return TechnicalIndicator(
                name="bb",
                value=float(current_price),
                signal=signal,
                strength=strength
            )

        except Exception as e:
            self.logger.error(f"Bollinger Bands calculation failed: {e}")
            return TechnicalIndicator(
                name="bb",
                value=0.0,
                signal="hold",
                strength=0.0
            )

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> TechnicalIndicator:
        """Calculate Average True Range indicator."""
        try:
            # Calculate True Range
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())

            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()

            current_atr = atr.iloc[-1]
            current_price = df['close'].iloc[-1]

            # ATR is typically used for volatility, not direct signals
            # But we can use it to adjust signal strength
            volatility_factor = min(current_atr / current_price, 1.0) if current_price > 0 else 0.0

            return TechnicalIndicator(
                name="atr",
                value=float(current_atr),
                signal="hold",  # ATR doesn't provide directional signals
                strength=volatility_factor
            )

        except Exception as e:
            self.logger.error(f"ATR calculation failed: {e}")
            return TechnicalIndicator(
                name="atr",
                value=0.0,
                signal="hold",
                strength=0.0
            )

    def _calculate_sma(self, df: pd.DataFrame, period: int = 20) -> TechnicalIndicator:
        """Calculate Simple Moving Average indicator."""
        try:
            sma = df['close'].rolling(window=period).mean()
            current_sma = sma.iloc[-1]
            current_price = df['close'].iloc[-1]

            # Determine signal based on price vs SMA
            if current_price > current_sma:
                signal = "buy"
                strength = min((current_price - current_sma) / current_sma, 1.0)
            elif current_price < current_sma:
                signal = "sell"
                strength = min((current_sma - current_price) / current_sma, 1.0)
            else:
                signal = "hold"
                strength = 0.0

            return TechnicalIndicator(
                name="sma",
                value=float(current_sma),
                signal=signal,
                strength=strength
            )

        except Exception as e:
            self.logger.error(f"SMA calculation failed: {e}")
            return TechnicalIndicator(
                name="sma",
                value=0.0,
                signal="hold",
                strength=0.0
            )

    def _determine_overall_signal(self, indicators: dict[str, TechnicalIndicator]) -> tuple[SignalType, float]:
        """Determine overall signal from all indicators."""
        buy_signals = 0
        sell_signals = 0
        total_strength = 0.0

        for indicator in indicators.values():
            if indicator.signal == "buy":
                buy_signals += 1
                total_strength += indicator.strength
            elif indicator.signal == "sell":
                sell_signals += 1
                total_strength += indicator.strength

        # Determine signal type
        if buy_signals > sell_signals:
            signal_type = SignalType.BUY
        elif sell_signals > buy_signals:
            signal_type = SignalType.SELL
        else:
            signal_type = SignalType.HOLD

        # Calculate confidence
        total_indicators = len(indicators)
        if total_indicators > 0:
            confidence = total_strength / total_indicators
        else:
            confidence = 0.0

        return signal_type, confidence

    async def _process_market_data(self, data: dict[str, Any]) -> None:
        """Process incoming market data."""
        # This could trigger automatic analysis or update internal state
        self.logger.debug(f"Processing market data for {data.get('symbol', 'unknown')}")

    def get_status(self) -> dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "ta_agent",
            "status": self.status.value,
            "analysis_count": self._analysis_count,
            "signal_count": self._signal_count,
            "last_analysis": self._last_analysis.timestamp.isoformat() if self._last_analysis else None,
            "indicators": self._indicators,
            "timeframes": self._timeframes
        }


# Tool classes for the TA agent

class TechnicalAnalysisTool(Tool):
    """Tool for performing technical analysis."""

    def __init__(self, ta_agent: TechnicalAnalysisAgent):
        super().__init__("technical_analysis", "Perform technical analysis on market data")
        self.ta_agent = ta_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute technical analysis."""
        return await self.ta_agent._perform_technical_analysis(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol to analyze"
            },
            "timeframe": {
                "type": "string",
                "enum": ["1m", "5m", "15m", "1h", "4h", "1d"],
                "description": "Timeframe for analysis"
            },
            "ohlcv_data": {
                "type": "array",
                "description": "OHLCV data for analysis"
            }
        }


class IndicatorCalculationTool(Tool):
    """Tool for calculating specific indicators."""

    def __init__(self, ta_agent: TechnicalAnalysisAgent):
        super().__init__("indicator_calculation", "Calculate specific technical indicators")
        self.ta_agent = ta_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute indicator calculation."""
        return await self.ta_agent._calculate_indicator(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "indicator_name": {
                "type": "string",
                "enum": ["rsi", "macd", "bb", "atr", "sma"],
                "description": "Name of the indicator to calculate"
            },
            "ohlcv_data": {
                "type": "array",
                "description": "OHLCV data for calculation"
            }
        }
