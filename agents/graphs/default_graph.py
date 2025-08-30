"""
Default Task Graph for AiBotBS Agent System.
Defines the standard workflow: Orchestrator → (TA, ML, News) → Scoring → Risk → Execution
"""


from ..core.base import Message, MessageType
from ..core.router import Route, RouteStep, RouteType, TaskGraph


def create_default_task_graph() -> TaskGraph:
    """Create the default task graph for the agent system."""

    # Create the main task graph
    task_graph = TaskGraph(
        id="default",
        name="default_trading_workflow",
        description="Standard trading workflow: Analysis → Scoring → Risk → Execution",
        routes=[]
    )

    # Route 1: Market Analysis (Parallel execution of TA, ML, and News)
    market_analysis_route = Route(
        id="market_analysis",
        name="market_analysis",
        description="Parallel execution of Technical Analysis, Machine Learning, and News Analysis",
        type=RouteType.PARALLEL,
        steps=[],
        metadata={
            "timeout": 300,  # 5 minutes
            "max_concurrent": 3
        }
    )

    # Add TA analysis step
    ta_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="ta_agent",
        subject="technical_analysis",
        body={
            "task_type": "analyze",
            "symbols": ["BTC-USDT", "ETH-USDT"],
            "timeframes": ["1h", "4h", "1d"],
            "indicators": ["RSI", "MACD", "BB", "ATR", "SMA"]
        }
    )

    ta_step = RouteStep(
        id="technical_analysis",
        agent_id="ta_agent",
        message=ta_message,
        timeout=120,
        max_retries=2
    )
    market_analysis_route.steps.append(ta_step)

    # Add ML analysis step
    ml_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="ml_agent",
        subject="machine_learning_analysis",
        body={
            "task_type": "predict",
            "symbols": ["BTC-USDT", "ETH-USDT"],
            "models": ["RF", "LR", "GB"],
            "features": ["price", "volume", "technical_indicators"],
            "prediction_horizon": "1h"
        }
    )

    ml_step = RouteStep(
        id="machine_learning_analysis",
        agent_id="ml_agent",
        message=ml_message,
        timeout=180,
        max_retries=2
    )
    market_analysis_route.steps.append(ml_step)

    # Add News analysis step
    news_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="news_agent",
        subject="news_sentiment_analysis",
        body={
            "task_type": "analyze_sentiment",
            "sources": ["cryptocompare", "cryptopanic", "coinstats"],
            "keywords": ["bitcoin", "ethereum", "crypto", "blockchain"],
            "sentiment_analysis": True,
            "gpt_summary": True
        }
    )

    news_step = RouteStep(
        id="news_sentiment_analysis",
        agent_id="news_agent",
        message=news_message,
        timeout=90,
        max_retries=2
    )
    market_analysis_route.steps.append(news_step)

    # Route 2: Signal Generation and Scoring
    scoring_route = Route(
        id="signal_scoring",
        name="signal_scoring",
        description="Generate trading signals and calculate composite scores",
        type=RouteType.SEQUENTIAL,
        steps=[],
        metadata={
            "timeout": 120,
            "min_confidence": 0.7
        }
    )

    # Add signal generation step
    signal_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="signal_agent",
        subject="generate_signals",
        body={
            "task_type": "generate_signal",
            "ta_weight": 0.4,
            "ml_weight": 0.4,
            "news_weight": 0.2,
            "min_score": 0.6
        }
    )

    signal_step = RouteStep(
        id="generate_signals",
        agent_id="signal_agent",
        message=signal_message,
        dependencies=["technical_analysis", "machine_learning_analysis", "news_sentiment_analysis"],
        timeout=60,
        max_retries=1
    )
    scoring_route.steps.append(signal_step)

    # Add composite scoring step
    composite_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="scoring_agent",
        subject="composite_scoring",
        body={
            "task_type": "calculate_score",
            "scoring_method": "weighted_average",
            "normalize_scores": True,
            "apply_thresholds": True
        }
    )

    composite_step = RouteStep(
        id="composite_scoring",
        agent_id="scoring_agent",
        message=composite_message,
        dependencies=["generate_signals"],
        timeout=60,
        max_retries=1
    )
    scoring_route.steps.append(composite_step)

    # Route 3: Risk Assessment
    risk_route = Route(
        id="risk_assessment",
        name="risk_assessment",
        description="Assess risk and validate trading decisions",
        type=RouteType.SEQUENTIAL,
        steps=[],
        metadata={
            "timeout": 90,
            "max_risk_per_trade": 0.02,  # 2% max risk per trade
            "max_portfolio_risk": 0.1     # 10% max portfolio risk
        }
    )

    # Add risk validation step
    risk_validation_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="risk_agent",
        subject="validate_risk",
        body={
            "task_type": "validate_risk",
            "check_position_limits": True,
            "check_balance": True,
            "check_correlation": True,
            "max_leverage": 3.0
        }
    )

    risk_validation_step = RouteStep(
        id="validate_risk",
        agent_id="risk_agent",
        message=risk_validation_message,
        dependencies=["composite_scoring"],
        timeout=60,
        max_retries=1
    )
    risk_route.steps.append(risk_validation_step)

    # Add portfolio risk check step
    portfolio_risk_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="risk_agent",
        subject="portfolio_risk_check",
        body={
            "task_type": "check_portfolio_risk",
            "check_portfolio_concentration": True,
            "check_sector_exposure": True,
            "check_volatility_limits": True
        }
    )

    portfolio_risk_step = RouteStep(
        id="portfolio_risk_check",
        agent_id="risk_agent",
        message=portfolio_risk_message,
        dependencies=["validate_risk"],
        timeout=60,
        max_retries=1
    )
    risk_route.steps.append(portfolio_risk_step)

    # Route 4: Trade Execution
    execution_route = Route(
        id="trade_execution",
        name="trade_execution",
        description="Execute approved trades with proper order management",
        type=RouteType.SEQUENTIAL,
        steps=[],
        metadata={
            "timeout": 180,
            "slippage_tolerance": 0.001,  # 0.1% slippage tolerance
            "partial_fill_handling": True
        }
    )

    # Add order placement step
    order_placement_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="execution_agent",
        subject="place_orders",
        body={
            "task_type": "place_order",
            "order_type": "limit",
            "time_in_force": "GTC",
            "reduce_only": False,
            "post_only": False
        }
    )

    order_placement_step = RouteStep(
        id="place_orders",
        agent_id="execution_agent",
        message=order_placement_message,
        dependencies=["portfolio_risk_check"],
        timeout=90,
        max_retries=2
    )
    execution_route.steps.append(order_placement_step)

    # Add bracket order management step
    bracket_management_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="execution_agent",
        subject="manage_bracket_orders",
        body={
            "task_type": "manage_bracket",
            "auto_tp_sl": True,
            "tp_percentage": 0.03,  # 3% take profit
            "sl_percentage": 0.02,  # 2% stop loss
            "trailing_stop": False
        }
    )

    bracket_management_step = RouteStep(
        id="manage_bracket_orders",
        agent_id="execution_agent",
        message=bracket_management_message,
        dependencies=["place_orders"],
        timeout=90,
        max_retries=2
    )
    execution_route.steps.append(bracket_management_step)

    # Route 5: Portfolio Update and Monitoring
    monitoring_route = Route(
        id="portfolio_monitoring",
        name="portfolio_monitoring",
        description="Update portfolio and monitor active positions",
        type=RouteType.SEQUENTIAL,
        steps=[],
        metadata={
            "timeout": 60,
            "update_interval": 300  # 5 minutes
        }
    )

    # Add portfolio update step
    portfolio_update_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="portfolio_agent",
        subject="update_portfolio",
        body={
            "task_type": "update_portfolio",
            "update_positions": True,
            "update_pnl": True,
            "update_risk_metrics": True
        }
    )

    portfolio_update_step = RouteStep(
        id="update_portfolio",
        agent_id="portfolio_agent",
        message=portfolio_update_message,
        dependencies=["manage_bracket_orders"],
        timeout=30,
        max_retries=1
    )
    monitoring_route.steps.append(portfolio_update_step)

    # Add position monitoring step
    position_monitoring_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="portfolio_agent",
        subject="monitor_positions",
        body={
            "task_type": "monitor_positions",
            "check_stop_losses": True,
            "check_take_profits": True,
            "rebalance_if_needed": False
        }
    )

    position_monitoring_step = RouteStep(
        id="monitor_positions",
        agent_id="portfolio_agent",
        message=position_monitoring_message,
        dependencies=["update_portfolio"],
        timeout=30,
        max_retries=1
    )
    monitoring_route.steps.append(position_monitoring_step)

    # Add all routes to the task graph
    task_graph.routes = [
        market_analysis_route,
        scoring_route,
        risk_route,
        execution_route,
        monitoring_route
    ]

    return task_graph


def create_quick_analysis_graph() -> TaskGraph:
    """Create a quick analysis graph for rapid market assessment."""

    task_graph = TaskGraph(
        id="quick_market_analysis",
        name="quick_market_analysis",
        description="Rapid market analysis for quick decision making",
        routes=[]
    )

    # Quick analysis route (parallel execution)
    quick_route = Route(
        id="quick_analysis",
        name="quick_analysis",
        description="Quick parallel analysis of market conditions",
        type=RouteType.PARALLEL,
        metadata={
            "timeout": 60,  # 1 minute
            "max_concurrent": 3
        },
        steps=[]
    )

    # Quick TA check
    quick_ta_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="ta_agent",
        subject="quick_ta",
        body={
            "task_type": "quick_ta",
            "symbols": ["BTC-USDT"],
            "timeframes": ["1h"],
            "indicators": ["RSI", "MACD"],
            "quick_mode": True
        }
    )

    quick_ta_step = RouteStep(
        id="quick_ta",
        agent_id="ta_agent",
        message=quick_ta_message,
        timeout=20,
        max_retries=1
    )
    quick_route.steps.append(quick_ta_step)

    # Quick ML prediction
    quick_ml_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="ml_agent",
        subject="quick_ml",
        body={
            "task_type": "quick_ml",
            "symbols": ["BTC-USDT"],
            "models": ["RF"],
            "quick_prediction": True
        }
    )

    quick_ml_step = RouteStep(
        id="quick_ml",
        agent_id="ml_agent",
        message=quick_ml_message,
        timeout=20,
        max_retries=1
    )
    quick_route.steps.append(quick_ml_step)

    # Quick news check
    quick_news_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="news_agent",
        subject="quick_news",
        body={
            "task_type": "quick_news",
            "sources": ["cryptocompare"],
            "limit": 5,
            "quick_sentiment": True
        }
    )

    quick_news_step = RouteStep(
        id="quick_news",
        agent_id="news_agent",
        message=quick_news_message,
        timeout=20,
        max_retries=1
    )
    quick_route.steps.append(quick_news_step)

    # Quick scoring
    quick_scoring_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="scoring_agent",
        subject="quick_scoring",
        body={
            "task_type": "quick_scoring",
            "scoring_method": "simple_average",
            "quick_mode": True
        }
    )

    quick_scoring_step = RouteStep(
        id="quick_scoring",
        agent_id="scoring_agent",
        message=quick_scoring_message,
        dependencies=["quick_ta", "quick_ml", "quick_news"],
        timeout=30,
        max_retries=1
    )
    quick_route.steps.append(quick_scoring_step)

    task_graph.routes = [quick_route]
    return task_graph


def create_backtest_graph() -> TaskGraph:
    """Create a backtest graph for strategy testing."""

    task_graph = TaskGraph(
        id="strategy_backtest",
        name="strategy_backtest",
        description="Backtest trading strategies with historical data",
        routes=[]
    )

    # Data preparation route
    data_route = Route(
        id="data_preparation",
        name="data_preparation",
        description="Prepare historical data for backtesting",
        type=RouteType.SEQUENTIAL,
        metadata={
            "timeout": 300,
            "data_quality_check": True
        },
        steps=[]
    )

    data_prep_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="data_agent",
        subject="prepare_data",
        body={
            "task_type": "prepare_data",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31",
            "symbols": ["BTC-USDT", "ETH-USDT"],
            "timeframes": ["1h", "4h", "1d"],
            "include_indicators": True
        }
    )

    data_prep_step = RouteStep(
        id="prepare_data",
        agent_id="data_agent",
        message=data_prep_message,
        timeout=180,
        max_retries=2
    )
    data_route.steps.append(data_prep_step)

    # Strategy execution route
    strategy_route = Route(
        id="strategy_execution",
        name="strategy_execution",
        description="Execute backtest strategy",
        type=RouteType.SEQUENTIAL,
        metadata={
            "timeout": 600,
            "initial_capital": 10000,
            "commission": 0.001
        },
        steps=[]
    )

    strategy_exec_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="backtest_agent",
        subject="execute_strategy",
        body={
            "task_type": "execute_strategy",
            "strategy_name": "default_strategy",
            "risk_management": True,
            "position_sizing": True
        }
    )

    strategy_exec_step = RouteStep(
        id="execute_strategy",
        agent_id="backtest_agent",
        message=strategy_exec_message,
        dependencies=["prepare_data"],
        timeout=300,
        max_retries=1
    )
    strategy_route.steps.append(strategy_exec_step)

    # Results analysis route
    analysis_route = Route(
        id="results_analysis",
        name="results_analysis",
        description="Analyze backtest results",
        type=RouteType.SEQUENTIAL,
        metadata={
            "timeout": 120,
            "generate_report": True
        },
        steps=[]
    )

    results_analysis_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="analysis_agent",
        subject="analyze_results",
        body={
            "task_type": "analyze_results",
            "calculate_metrics": True,
            "generate_charts": True,
            "risk_analysis": True
        }
    )

    results_analysis_step = RouteStep(
        id="analyze_results",
        agent_id="analysis_agent",
        message=results_analysis_message,
        dependencies=["execute_strategy"],
        timeout=120,
        max_retries=1
    )
    analysis_route.steps.append(results_analysis_step)

    task_graph.routes = [data_route, strategy_route, analysis_route]
    return task_graph


def create_risk_monitoring_graph() -> TaskGraph:
    """Create a risk monitoring graph for continuous risk assessment."""

    task_graph = TaskGraph(
        id="continuous_risk_monitoring",
        name="continuous_risk_monitoring",
        description="Continuous monitoring of portfolio risk and market conditions",
        routes=[]
    )

    # Market risk monitoring route
    market_risk_route = Route(
        id="market_risk_monitoring",
        name="market_risk_monitoring",
        description="Monitor market-wide risk factors",
        type=RouteType.PARALLEL,
        metadata={
            "timeout": 120,
            "update_interval": 300
        },
        steps=[]
    )

    volatility_monitoring_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="risk_agent",
        subject="monitor_volatility",
        body={
            "task_type": "monitor_volatility",
            "calculate_var": True,
            "volatility_threshold": 0.5,
            "alert_on_breach": True
        }
    )

    volatility_monitoring_step = RouteStep(
        id="monitor_volatility",
        agent_id="risk_agent",
        message=volatility_monitoring_message,
        timeout=60,
        max_retries=1
    )
    market_risk_route.steps.append(volatility_monitoring_step)

    correlation_monitoring_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="risk_agent",
        subject="monitor_correlations",
        body={
            "task_type": "monitor_correlations",
            "correlation_threshold": 0.8,
            "update_frequency": "5m"
        }
    )

    correlation_monitoring_step = RouteStep(
        id="monitor_correlations",
        agent_id="risk_agent",
        message=correlation_monitoring_message,
        timeout=60,
        max_retries=1
    )
    market_risk_route.steps.append(correlation_monitoring_step)

    # Portfolio risk monitoring route
    portfolio_risk_route = Route(
        id="portfolio_risk_monitoring",
        name="portfolio_risk_monitoring",
        description="Monitor portfolio-specific risk metrics",
        type=RouteType.SEQUENTIAL,
        metadata={
            "timeout": 90,
            "update_interval": 300
        },
        steps=[]
    )

    position_risk_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="risk_agent",
        subject="assess_position_risk",
        body={
            "task_type": "assess_position_risk",
            "check_margin_requirements": True,
            "check_position_limits": True,
            "calculate_unrealized_pnl": True
        }
    )

    position_risk_step = RouteStep(
        id="assess_position_risk",
        agent_id="risk_agent",
        message=position_risk_message,
        dependencies=["monitor_volatility", "monitor_correlations"],
        timeout=60,
        max_retries=1
    )
    portfolio_risk_route.steps.append(position_risk_step)

    portfolio_metrics_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="portfolio_agent",
        subject="calculate_portfolio_metrics",
        body={
            "task_type": "calculate_portfolio_metrics",
            "calculate_sharpe_ratio": True,
            "calculate_max_drawdown": True,
            "calculate_risk_adjusted_returns": True
        }
    )

    portfolio_metrics_step = RouteStep(
        id="calculate_portfolio_metrics",
        agent_id="portfolio_agent",
        message=portfolio_metrics_message,
        dependencies=["assess_position_risk"],
        timeout=60,
        max_retries=1
    )
    portfolio_risk_route.steps.append(portfolio_metrics_step)

    # Alert generation route
    alert_route = Route(
        id="risk_alerts",
        name="risk_alerts",
        description="Generate risk alerts based on monitoring results",
        type=RouteType.SEQUENTIAL,
        metadata={
            "timeout": 30,
            "alert_channels": ["telegram", "email"]
        },
        steps=[]
    )

    alert_generation_message = Message(
        type=MessageType.TASK,
        from_agent="orchestrator",
        to_agent="alert_agent",
        subject="generate_alerts",
        body={
            "task_type": "generate_alerts",
            "risk_thresholds": {
                "var_limit": 0.02,
                "drawdown_limit": 0.1,
                "correlation_limit": 0.8
            },
            "notification_priority": "high"
        }
    )

    alert_generation_step = RouteStep(
        id="generate_alerts",
        agent_id="alert_agent",
        message=alert_generation_message,
        dependencies=["calculate_portfolio_metrics"],
        timeout=30,
        max_retries=1
    )
    alert_route.steps.append(alert_generation_step)

    task_graph.routes = [market_risk_route, portfolio_risk_route, alert_route]
    return task_graph


# Graph registry
AVAILABLE_GRAPHS = {
    "default_trading_workflow": create_default_task_graph,
    "quick_market_analysis": create_quick_analysis_graph,
    "strategy_backtest": create_backtest_graph,
    "continuous_risk_monitoring": create_risk_monitoring_graph
}


def get_available_graphs() -> dict[str, str]:
    """Get list of available task graphs with descriptions."""
    return {
        name: func().description
        for name, func in AVAILABLE_GRAPHS.items()
    }


def create_graph_by_name(name: str) -> TaskGraph:
    """Create a task graph by name."""
    if name not in AVAILABLE_GRAPHS:
        raise ValueError(f"Unknown task graph: {name}")

    return AVAILABLE_GRAPHS[name]()
