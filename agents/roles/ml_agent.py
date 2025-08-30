"""
Machine Learning Agent for AiBotBS.
Performs ML model inference, feature engineering, and predictions.
"""

import asyncio
import pickle
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from domain.errors import AgentError
from domain.models import SignalType

from ..core.base import BaseAgent, Message, MessageType
from ..core.tools import Tool, ToolCategory


@dataclass
class MLPrediction:
    """Machine learning prediction result."""
    model_name: str
    symbol: str
    timestamp: datetime
    prediction: SignalType
    confidence: float
    probabilities: dict[str, float]
    features: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelInfo:
    """Information about a trained model."""
    name: str
    model_type: str
    version: str
    training_date: datetime
    performance_metrics: dict[str, float]
    feature_names: list[str]
    model_path: str
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


class MachineLearningAgent(BaseAgent):
    """Machine learning agent that performs model inference and predictions."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "ml_agent", config)

        # ML configuration
        self._models_dir = Path(config.get("models_dir", "models"))
        self._default_model = config.get("default_model", "ensemble")
        self._fallback_signal = SignalType.HOLD
        self._confidence_threshold = config.get("confidence_threshold", 0.6)
        self._feature_engineering_config = config.get("feature_engineering", {})

        # Model registry
        self._models: dict[str, ModelInfo] = {}
        self._loaded_models: dict[str, Any] = {}
        self._scalers: dict[str, StandardScaler] = {}

        # Performance tracking
        self._prediction_count = 0
        self._high_confidence_count = 0
        self._last_prediction = None

        # Register message handlers
        self._register_message_handlers()

        # Register tools
        self._register_tools()

    async def _initialize(self) -> None:
        """Initialize the ML agent."""
        self.logger.info("Initializing machine learning agent")

        # Create models directory if it doesn't exist
        self._models_dir.mkdir(exist_ok=True)

        # Load available models
        await self._load_available_models()

        # Load default model
        if self._default_model in self._models:
            await self._load_model(self._default_model)

        # Start model monitoring
        asyncio.create_task(self._model_monitor())

        self.logger.info("Machine learning agent initialized")

    async def _cleanup(self) -> None:
        """Cleanup when stopping the agent."""
        self.logger.info("Cleaning up machine learning agent")

        # Clear loaded models
        self._loaded_models.clear()
        self._scalers.clear()

        self.logger.info("Machine learning agent cleanup completed")

    def _register_message_handlers(self) -> None:
        """Register message handlers."""
        self.register_message_handler(MessageType.TASK, self._handle_task_message)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

    def _register_tools(self) -> None:
        """Register ML-specific tools."""
        from ..core.tools import get_tool_registry

        registry = get_tool_registry()
        registry.register_tool(MLPredictionTool(self), ToolCategory.ANALYSIS)
        registry.register_tool(ModelManagementTool(self), ToolCategory.UTILITY)
        registry.register_tool(FeatureEngineeringTool(self), ToolCategory.ANALYSIS)

    async def _load_available_models(self) -> None:
        """Load information about available models."""
        try:
            if not self._models_dir.exists():
                self.logger.warning(f"Models directory does not exist: {self._models_dir}")
                return

            # Look for model files
            for model_file in self._models_dir.glob("*.pkl"):
                try:
                    model_info = await self._extract_model_info(model_file)
                    if model_info:
                        self._models[model_info.name] = model_info
                        self.logger.info(f"Found model: {model_info.name}")
                except Exception as e:
                    self.logger.error(f"Failed to load model info for {model_file}: {e}")

            # If no models found, create default models
            if not self._models:
                await self._create_default_models()

        except Exception as e:
            self.logger.error(f"Failed to load available models: {e}")

    async def _extract_model_info(self, model_file: Path) -> ModelInfo | None:
        """Extract model information from a model file."""
        try:
            # Try to load the model to extract info
            with open(model_file, 'rb') as f:
                model_data = pickle.load(f)

            if isinstance(model_data, dict) and 'model_info' in model_data:
                return model_data['model_info']
            else:
                # Create basic model info
                return ModelInfo(
                    name=model_file.stem,
                    model_type="unknown",
                    version="1.0",
                    training_date=datetime.utcnow(),
                    performance_metrics={},
                    feature_names=[],
                    model_path=str(model_file),
                    is_active=True
                )

        except Exception as e:
            self.logger.error(f"Failed to extract model info from {model_file}: {e}")
            return None

    async def _create_default_models(self) -> None:
        """Create default ML models if none exist."""
        try:
            self.logger.info("Creating default ML models")

            # Create a simple ensemble model
            ensemble_model = self._create_ensemble_model()

            # Save the model
            model_path = self._models_dir / "default_ensemble.pkl"
            model_info = ModelInfo(
                name="default_ensemble",
                model_type="ensemble",
                version="1.0",
                training_date=datetime.utcnow(),
                performance_metrics={"accuracy": 0.5},
                feature_names=["feature_1", "feature_2", "feature_3"],
                model_path=str(model_path),
                is_active=True
            )

            model_data = {
                'model': ensemble_model,
                'model_info': model_info,
                'scaler': StandardScaler()
            }

            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)

            self._models["default_ensemble"] = model_info
            self.logger.info("Created default ensemble model")

        except Exception as e:
            self.logger.error(f"Failed to create default models: {e}")

    def _create_ensemble_model(self) -> Any:
        """Create a simple ensemble model."""
        # This is a placeholder - in practice, you'd load pre-trained models
        models = {
            'rf': RandomForestClassifier(n_estimators=100, random_state=42),
            'gb': GradientBoostingClassifier(n_estimators=100, random_state=42),
            'lr': LogisticRegression(random_state=42)
        }
        return models

    async def _load_model(self, model_name: str) -> bool:
        """Load a specific model into memory."""
        try:
            if model_name not in self._models:
                self.logger.error(f"Model not found: {model_name}")
                return False

            model_info = self._models[model_name]
            model_path = Path(model_info.model_path)

            if not model_path.exists():
                self.logger.error(f"Model file not found: {model_path}")
                return False

            # Load model data
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            self._loaded_models[model_name] = model_data['model']
            if 'scaler' in model_data:
                self._scalers[model_name] = model_data['scaler']

            self.logger.info(f"Loaded model: {model_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            return False

    async def _model_monitor(self) -> None:
        """Monitor model performance and health."""
        while self._running:
            try:
                # Check model health
                await self._check_model_health()

                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                self.logger.error(f"Model monitor error: {e}")
                await asyncio.sleep(300)

    async def _check_model_health(self) -> None:
        """Check the health of loaded models."""
        for model_name in list(self._loaded_models.keys()):
            try:
                # Basic health check - try to make a prediction with dummy data
                dummy_features = np.random.random((1, 3))
                model = self._loaded_models[model_name]

                if hasattr(model, 'predict'):
                    _ = model.predict(dummy_features)
                else:
                    # Handle ensemble models
                    for submodel in model.values():
                        if hasattr(submodel, 'predict'):
                            _ = submodel.predict(dummy_features)

            except Exception as e:
                self.logger.warning(f"Model {model_name} health check failed: {e}")
                # Reload the model
                await self._load_model(model_name)

    async def _handle_task_message(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "ml_prediction":
                result = await self._make_prediction(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="ml_prediction_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            elif task_type == "feature_engineering":
                result = await self._engineer_features(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="feature_engineering_result",
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
        if data_type == "market_data":
            await self._process_market_data(message.body)

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        command = message.body.get("command")
        parameters = message.body.get("parameters", {})

        try:
            if command == "get_status":
                result = self.get_status()
            elif command == "list_models":
                result = {
                    "models": [model.name for model in self._models.values()],
                    "loaded_models": list(self._loaded_models.keys())
                }
            elif command == "load_model":
                model_name = parameters.get("model_name")
                if not model_name:
                    raise AgentError("Missing model_name parameter")

                success = await self._load_model(model_name)
                result = {"status": "loaded" if success else "failed", "model_name": model_name}

            elif command == "get_model_info":
                model_name = parameters.get("model_name")
                if not model_name:
                    raise AgentError("Missing model_name parameter")

                if model_name in self._models:
                    model_info = self._models[model_name]
                    result = {
                        "name": model_info.name,
                        "type": model_info.model_type,
                        "version": model_info.version,
                        "training_date": model_info.training_date.isoformat(),
                        "performance_metrics": model_info.performance_metrics,
                        "feature_names": model_info.feature_names,
                        "is_active": model_info.is_active
                    }
                else:
                    result = {"error": f"Model not found: {model_name}"}

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

    async def _make_prediction(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Make a prediction using the loaded model."""
        try:
            symbol = parameters.get("symbol")
            features = parameters.get("features")
            model_name = parameters.get("model_name", self._default_model)

            if not symbol or not features:
                raise AgentError("Missing required parameters: symbol or features")

            # Ensure model is loaded
            if model_name not in self._loaded_models:
                await self._load_model(model_name)
                if model_name not in self._loaded_models:
                    raise AgentError(f"Failed to load model: {model_name}")

            # Engineer features if needed
            if isinstance(features, dict):
                engineered_features = await self._engineer_features_from_dict(features)
            else:
                engineered_features = features

            # Make prediction
            prediction, confidence, probabilities = await self._predict_with_model(
                model_name, engineered_features
            )

            # Create prediction result
            ml_prediction = MLPrediction(
                model_name=model_name,
                symbol=symbol,
                timestamp=datetime.utcnow(),
                prediction=prediction,
                confidence=confidence,
                probabilities=probabilities,
                features=engineered_features
            )

            # Update statistics
            self._prediction_count += 1
            if confidence >= self._confidence_threshold:
                self._high_confidence_count += 1
            self._last_prediction = ml_prediction

            return {
                "symbol": symbol,
                "model_name": model_name,
                "prediction": prediction.value,
                "confidence": confidence,
                "probabilities": probabilities,
                "timestamp": ml_prediction.timestamp.isoformat()
            }

        except Exception as e:
            self.logger.error(f"ML prediction failed: {e}")
            # Return fallback signal
            return {
                "symbol": parameters.get("symbol", "unknown"),
                "model_name": "fallback",
                "prediction": self._fallback_signal.value,
                "confidence": 0.0,
                "probabilities": {self._fallback_signal.value: 1.0},
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }

    async def _predict_with_model(self, model_name: str, features: np.ndarray) -> tuple[SignalType, float, dict[str, float]]:
        """Make a prediction using a specific model."""
        try:
            model = self._loaded_models[model_name]

            # Scale features if scaler is available
            if model_name in self._scalers:
                features = self._scalers[model_name].transform(features.reshape(1, -1))
            else:
                features = features.reshape(1, -1)

            # Make prediction
            if hasattr(model, 'predict_proba'):
                probabilities = model.predict_proba(features)[0]
                prediction_idx = np.argmax(probabilities)
                confidence = probabilities[prediction_idx]

                # Map prediction index to signal type
                if len(probabilities) == 2:  # Binary classification
                    prediction = SignalType.BUY if prediction_idx == 1 else SignalType.SELL
                    prob_dict = {
                        SignalType.SELL.value: float(probabilities[0]),
                        SignalType.BUY.value: float(probabilities[1])
                    }
                else:  # Multi-class
                    signal_map = [SignalType.SELL, SignalType.HOLD, SignalType.BUY]
                    prediction = signal_map[min(prediction_idx, len(signal_map) - 1)]
                    prob_dict = {f"class_{i}": float(prob) for i, prob in enumerate(probabilities)}

            else:
                # Fallback for models without predict_proba
                prediction_raw = model.predict(features)[0]
                confidence = 0.5  # Default confidence

                if isinstance(prediction_raw, (int, float)):
                    if prediction_raw > 0.5:
                        prediction = SignalType.BUY
                    elif prediction_raw < -0.5:
                        prediction = SignalType.SELL
                    else:
                        prediction = SignalType.HOLD
                else:
                    prediction = SignalType.HOLD

                prob_dict = {prediction.value: confidence}

            return prediction, float(confidence), prob_dict

        except Exception as e:
            self.logger.error(f"Model prediction failed: {e}")
            return self._fallback_signal, 0.0, {self._fallback_signal.value: 1.0}

    async def _engineer_features(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Engineer features from raw data."""
        try:
            raw_data = parameters.get("raw_data")
            feature_type = parameters.get("feature_type", "basic")

            if not raw_data:
                raise AgentError("Missing required parameter: raw_data")

            if feature_type == "basic":
                features = await self._engineer_basic_features(raw_data)
            elif feature_type == "technical":
                features = await self._engineer_technical_features(raw_data)
            elif feature_type == "advanced":
                features = await self._engineer_advanced_features(raw_data)
            else:
                raise AgentError(f"Unknown feature type: {feature_type}")

            return {
                "features": features,
                "feature_type": feature_type,
                "feature_count": len(features)
            }

        except Exception as e:
            self.logger.error(f"Feature engineering failed: {e}")
            raise AgentError(f"Feature engineering failed: {e}")

    async def _engineer_features_from_dict(self, raw_features: dict[str, Any]) -> np.ndarray:
        """Engineer features from a dictionary of raw features."""
        try:
            # Convert dictionary to feature array
            feature_names = self._feature_engineering_config.get("feature_names", [])

            if feature_names:
                # Use predefined feature names
                features = []
                for name in feature_names:
                    if name in raw_features:
                        features.append(float(raw_features[name]))
                    else:
                        features.append(0.0)
            else:
                # Use all available features
                features = [float(v) for v in raw_features.values() if isinstance(v, (int, float))]

            return np.array(features)

        except Exception as e:
            self.logger.error(f"Feature engineering from dict failed: {e}")
            return np.array([0.0, 0.0, 0.0])  # Default features

    async def _engineer_basic_features(self, raw_data: dict[str, Any]) -> np.ndarray:
        """Engineer basic features from raw data."""
        try:
            features = []

            # Price-based features
            if 'price' in raw_data:
                features.append(float(raw_data['price']))
            if 'volume' in raw_data:
                features.append(float(raw_data['volume']))
            if 'market_cap' in raw_data:
                features.append(float(raw_data['market_cap']))

            # Time-based features
            if 'timestamp' in raw_data:
                timestamp = raw_data['timestamp']
                if isinstance(timestamp, str):
                    dt = datetime.fromisoformat(timestamp)
                else:
                    dt = timestamp
                features.extend([dt.hour, dt.weekday()])

            # Ensure minimum feature count
            while len(features) < 3:
                features.append(0.0)

            return np.array(features[:3])  # Return first 3 features

        except Exception as e:
            self.logger.error(f"Basic feature engineering failed: {e}")
            return np.array([0.0, 0.0, 0.0])

    async def _engineer_technical_features(self, raw_data: dict[str, Any]) -> np.ndarray:
        """Engineer technical features from raw data."""
        try:
            features = []

            # OHLCV features
            if 'ohlcv' in raw_data:
                ohlcv = raw_data['ohlcv']
                if len(ohlcv) >= 2:
                    current = ohlcv[-1]
                    previous = ohlcv[-2]

                    # Price change
                    price_change = (current['close'] - previous['close']) / previous['close']
                    features.append(price_change)

                    # Volume change
                    volume_change = (current['volume'] - previous['volume']) / previous['volume']
                    features.append(volume_change)

                    # Volatility
                    high_low = (current['high'] - current['low']) / current['close']
                    features.append(high_low)

            # Ensure minimum feature count
            while len(features) < 3:
                features.append(0.0)

            return np.array(features[:3])

        except Exception as e:
            self.logger.error(f"Technical feature engineering failed: {e}")
            return np.array([0.0, 0.0, 0.0])

    async def _engineer_advanced_features(self, raw_data: dict[str, Any]) -> np.ndarray:
        """Engineer advanced features from raw data."""
        try:
            features = []

            # Combine basic and technical features
            basic_features = await self._engineer_basic_features(raw_data)
            technical_features = await self._engineer_technical_features(raw_data)

            features.extend(basic_features)
            features.extend(technical_features)

            # Add interaction features
            if len(features) >= 2:
                interaction = features[0] * features[1]
                features.append(interaction)

            # Ensure minimum feature count
            while len(features) < 3:
                features.append(0.0)

            return np.array(features[:3])

        except Exception as e:
            self.logger.error(f"Advanced feature engineering failed: {e}")
            return np.array([0.0, 0.0, 0.0])

    async def _process_market_data(self, data: dict[str, Any]) -> None:
        """Process incoming market data."""
        # This could trigger automatic predictions or update internal state
        self.logger.debug(f"Processing market data for {data.get('symbol', 'unknown')}")

    def get_status(self) -> dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "ml_agent",
            "status": self.status.value,
            "prediction_count": self._prediction_count,
            "high_confidence_count": self._high_confidence_count,
            "last_prediction": self._last_prediction.timestamp.isoformat() if self._last_prediction else None,
            "available_models": len(self._models),
            "loaded_models": len(self._loaded_models),
            "default_model": self._default_model,
            "confidence_threshold": self._confidence_threshold
        }


# Tool classes for the ML agent

class MLPredictionTool(Tool):
    """Tool for making ML predictions."""

    def __init__(self, ml_agent: MachineLearningAgent):
        super().__init__("ml_prediction", "Make predictions using machine learning models")
        self.ml_agent = ml_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute ML prediction."""
        return await self.ml_agent._make_prediction(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol to predict"
            },
            "features": {
                "type": "object",
                "description": "Features for prediction"
            },
            "model_name": {
                "type": "string",
                "description": "Name of the model to use"
            }
        }


class ModelManagementTool(Tool):
    """Tool for managing ML models."""

    def __init__(self, ml_agent: MachineLearningAgent):
        super().__init__("model_management", "Manage machine learning models")
        self.ml_agent = ml_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute model management operation."""
        operation = parameters.get("operation")

        if operation == "list_models":
            return {
                "models": [model.name for model in self.ml_agent._models.values()],
                "loaded_models": list(self.ml_agent._loaded_models.keys())
            }
        elif operation == "load_model":
            model_name = parameters.get("model_name")
            if not model_name:
                raise AgentError("Missing model_name parameter")

            success = await self.ml_agent._load_model(model_name)
            return {"status": "loaded" if success else "failed", "model_name": model_name}
        else:
            raise AgentError(f"Unknown operation: {operation}")

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "operation": {
                "type": "string",
                "enum": ["list_models", "load_model"],
                "description": "Model management operation to perform"
            },
            "model_name": {
                "type": "string",
                "description": "Name of the model to load"
            }
        }


class FeatureEngineeringTool(Tool):
    """Tool for feature engineering."""

    def __init__(self, ml_agent: MachineLearningAgent):
        super().__init__("feature_engineering", "Engineer features from raw data")
        self.ml_agent = ml_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute feature engineering."""
        return await self.ml_agent._engineer_features(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "raw_data": {
                "type": "object",
                "description": "Raw data to engineer features from"
            },
            "feature_type": {
                "type": "string",
                "enum": ["basic", "technical", "advanced"],
                "description": "Type of features to engineer"
            }
        }
