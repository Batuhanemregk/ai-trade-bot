# 🤝 Contributing Guide

> **Development Guidelines and Contribution Standards**

## 🎯 Overview

Welcome to AiBotBS! This guide outlines the development standards, contribution process, and best practices for maintaining code quality and consistency.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- Basic understanding of Clean Architecture principles
- Familiarity with trading systems (optional but helpful)

### Development Setup
```bash
# Clone the repository
git clone <repository-url>
cd AiBotBS

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Verify setup
python -m compileall .
bash scripts/ci_smoke.sh
```

## 📋 Development Workflow

### 1. **Feature Development**
```bash
# Create feature branch
git checkout -b feature/your-feature-name

# Make changes
# ... edit files ...

# Stage changes
git add .

# Commit with proper message
git commit -m "feat: add new scoring algorithm"

# Push to remote
git push origin feature/your-feature-name
```

### 2. **Bug Fixes**
```bash
# Create bugfix branch
git checkout -b fix/issue-description

# Fix the issue
# ... edit files ...

# Commit fix
git commit -m "fix: resolve order execution timeout"

# Push and create PR
git push origin fix/issue-description
```

### 3. **Pull Request Process**
1. Create/update feature branch
2. Ensure all tests pass
3. Run code quality checks
4. Create pull request with detailed description
5. Address review feedback
6. Merge after approval

## 🏗️ Code Architecture

### Clean Architecture Principles
- **Domain Layer**: Business entities and rules
- **Application Layer**: Use cases and orchestration
- **Infrastructure Layer**: External interfaces and persistence
- **Interface Layer**: User interfaces and APIs

### Module Structure
```
src/
├── domain/           # Business entities, enums, value objects
├── application/      # Use cases, services, orchestration
├── infrastructure/   # External interfaces, databases, APIs
├── interface/        # Controllers, presenters, CLI
└── shared/           # Common utilities, exceptions, constants
```

### SOLID Principles
- **Single Responsibility**: Each class has one reason to change
- **Open/Closed**: Open for extension, closed for modification
- **Liskov Substitution**: Subtypes are substitutable
- **Interface Segregation**: Small, focused interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

## 🎨 Code Style

### Python Style Guide
Follow [PEP 8](https://pep8.org/) and project-specific conventions.

#### Naming Conventions
```python
# Classes: PascalCase
class TradingService:
    pass

# Functions and variables: snake_case
def calculate_position_size():
    pass

# Constants: UPPER_SNAKE_CASE
MAX_POSITION_SIZE = 0.1

# Private methods: _leading_underscore
def _internal_helper():
    pass
```

#### Type Hints
```python
from typing import Optional, List, Dict, Union
from decimal import Decimal

def execute_order(
    symbol: str,
    side: str,
    amount: Decimal,
    price: Optional[Decimal] = None
) -> Dict[str, Union[str, Decimal]]:
    """Execute a trading order."""
    pass
```

#### Docstrings
```python
def calculate_risk_score(
    position_size: float,
    volatility: float,
    correlation: float
) -> float:
    """
    Calculate risk score for a position.
    
    Args:
        position_size: Size of the position (0.0 to 1.0)
        volatility: Historical volatility of the asset
        correlation: Correlation with existing positions
        
    Returns:
        Risk score between 0.0 (low risk) and 1.0 (high risk)
        
    Raises:
        ValueError: If parameters are out of valid range
    """
    if not 0 <= position_size <= 1:
        raise ValueError("Position size must be between 0 and 1")
    
    # Implementation...
    return risk_score
```

### File Organization
```python
# Standard file structure
"""
File: trading_service.py
Description: Trading service implementation
Author: Your Name
Date: 2024-01-01
"""

# Imports: standard library first, then third-party, then local
import os
import sys
from typing import Dict, List, Optional
from decimal import Decimal

import ccxt
import pandas as pd

from domain.entities import Order, Position
from domain.exceptions import TradingError
from infrastructure.exchange_adapter import ExchangeAdapter

# Constants
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

# Classes
class TradingService:
    """Service for executing trading operations."""
    
    def __init__(self, exchange_adapter: ExchangeAdapter):
        self.exchange = exchange_adapter
        self.logger = logging.getLogger(__name__)
    
    # Public methods first
    async def execute_order(self, order: Order) -> Dict:
        """Execute a trading order."""
        pass
    
    # Private methods last
    def _validate_order(self, order: Order) -> bool:
        """Validate order parameters."""
        pass
```

## 🔧 Code Quality Tools

### Ruff (Linting)
Fast Python linter with auto-fix capabilities.

#### Configuration
```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 88
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]
"tests/**/*.py" = ["B011"]
```

#### Usage
```bash
# Check code
ruff check .

# Fix auto-fixable issues
ruff check --fix .

# Check specific file
ruff check src/trading_service.py

# Show rule explanations
ruff rule E501
```

### Black (Code Formatting)
Uncompromising Python code formatter.

#### Configuration
```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''
```

#### Usage
```bash
# Format code
black .

# Check formatting without changing
black --check .

# Format specific file
black src/trading_service.py

# Show diff
black --diff .
```

### MyPy (Type Checking)
Static type checker for Python.

#### Configuration
```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

[[tool.mypy.overrides]]
module = [
    "ccxt.*",
    "pandas.*",
    "numpy.*",
    "scipy.*",
    "sklearn.*",
]
ignore_missing_imports = true
```

#### Usage
```bash
# Type check entire project
mypy .

# Type check specific file
mypy src/trading_service.py

# Show error codes
mypy --show-error-codes .

# Generate HTML report
mypy --html-report reports/mypy .
```

### Pre-commit Hooks
Automated checks before commits.

#### Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        language_version: python3.11
        
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
        
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
        
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: pytest
        language: system
        pass_filenames: false
        always_run: true
        args: ["-x", "-m", "core"]
```

#### Usage
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
```

## 📝 Commit Messages

### Conventional Commits
Follow [Conventional Commits](https://www.conventionalcommits.org/) specification.

#### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

#### Examples
```bash
# Feature
git commit -m "feat: add machine learning scoring algorithm"

# Bug fix
git commit -m "fix: resolve order execution timeout issue"

# Documentation
git commit -m "docs: update API documentation with examples"

# Refactoring
git commit -m "refactor: extract scoring logic into separate service"

# Test
git commit -m "test: add integration tests for trade service"

# Breaking change
git commit -m "feat!: change scoring API to use async methods

BREAKING CHANGE: Scoring functions now return awaitable objects"
```

#### Scope Examples
```bash
# With scope
git commit -m "feat(scoring): add composite signal aggregation"
git commit -m "fix(execution): resolve bracket order attachment issue"
git commit -m "refactor(telegram): simplify command handler structure"
```

## 🔍 Code Review Guidelines

### Review Checklist
- [ ] Code follows project architecture
- [ ] SOLID principles are respected
- [ ] Type hints are complete and accurate
- [ ] Tests cover new functionality
- [ ] Documentation is updated
- [ ] No breaking changes (unless intentional)
- [ ] Performance considerations addressed
- [ ] Security implications considered
- [ ] Error handling is robust
- [ ] Logging is appropriate

### Review Comments
```python
# Good review comment
"""
Consider extracting this validation logic into a separate method:
- Improves testability
- Follows single responsibility principle
- Makes the code more reusable
"""

# Bad review comment
"Fix this"
```

### Review Process
1. **Initial Review**: Check for obvious issues
2. **Deep Review**: Analyze logic and architecture
3. **Testing Review**: Verify test coverage and quality
4. **Documentation Review**: Check docs and comments
5. **Final Approval**: Approve or request changes

## 🧪 Testing Standards

### Test Requirements
- **Unit Tests**: >90% coverage for new code
- **Integration Tests**: Cover main workflows
- **Performance Tests**: For critical paths
- **Error Tests**: Test error conditions

### Test Structure
```python
import pytest
from unittest.mock import Mock, patch

class TestTradingService:
    """Test suite for TradingService."""
    
    @pytest.fixture
    def mock_exchange(self):
        """Mock exchange adapter."""
        return Mock(spec=ExchangeAdapter)
    
    @pytest.fixture
    def trading_service(self, mock_exchange):
        """Trading service instance for testing."""
        return TradingService(mock_exchange)
    
    def test_execute_order_success(self, trading_service, mock_exchange):
        """Test successful order execution."""
        # Arrange
        order = Order(symbol="BTC-USDT", side="buy", amount=0.1)
        mock_exchange.place_order.return_value = {"status": "success"}
        
        # Act
        result = trading_service.execute_order(order)
        
        # Assert
        assert result["status"] == "success"
        mock_exchange.place_order.assert_called_once_with(order)
    
    def test_execute_order_failure(self, trading_service, mock_exchange):
        """Test order execution failure."""
        # Arrange
        order = Order(symbol="BTC-USDT", side="buy", amount=0.1)
        mock_exchange.place_order.side_effect = TradingError("Insufficient balance")
        
        # Act & Assert
        with pytest.raises(TradingError, match="Insufficient balance"):
            trading_service.execute_order(order)
```

## 📚 Documentation Standards

### Code Documentation
- **Docstrings**: All public functions and classes
- **Type Hints**: Complete type annotations
- **Comments**: Explain complex logic
- **Examples**: Include usage examples

### API Documentation
- **README**: Project overview and quick start
- **API Docs**: Detailed interface documentation
- **Examples**: Working code examples
- **Troubleshooting**: Common issues and solutions

### Documentation Examples
```python
class TradingService:
    """
    Service for executing trading operations.
    
    This service provides a high-level interface for trading operations,
    including order execution, position management, and risk control.
    
    Example:
        >>> service = TradingService(exchange_adapter)
        >>> result = await service.execute_order(order)
        >>> print(f"Order executed: {result['status']}")
    """
    
    def __init__(self, exchange_adapter: ExchangeAdapter):
        """
        Initialize the trading service.
        
        Args:
            exchange_adapter: Adapter for exchange communication
            
        Raises:
            ValueError: If exchange_adapter is None
        """
        if exchange_adapter is None:
            raise ValueError("Exchange adapter cannot be None")
        
        self.exchange = exchange_adapter
        self.logger = logging.getLogger(__name__)
    
    async def execute_order(self, order: Order) -> Dict[str, Any]:
        """
        Execute a trading order.
        
        This method handles the complete order execution flow:
        1. Order validation
        2. Risk checks
        3. Exchange submission
        4. Status monitoring
        
        Args:
            order: The order to execute
            
        Returns:
            Dictionary containing execution result
            
        Raises:
            TradingError: If order execution fails
            ValidationError: If order is invalid
        """
        # Implementation...
        pass
```

## 🚨 Error Handling

### Exception Hierarchy
```python
class AiBotBSError(Exception):
    """Base exception for AiBotBS."""
    pass

class ValidationError(AiBotBSError):
    """Validation error."""
    pass

class TradingError(AiBotBSError):
    """Trading operation error."""
    pass

class ExchangeError(TradingError):
    """Exchange communication error."""
    pass

class RiskError(TradingError):
    """Risk management error."""
    pass
```

### Error Handling Patterns
```python
def execute_trade(self, order: Order) -> Dict:
    """Execute a trade with proper error handling."""
    try:
        # Validate order
        self._validate_order(order)
        
        # Check risk limits
        self._check_risk_limits(order)
        
        # Execute order
        result = self.exchange.place_order(order)
        
        # Log success
        self.logger.info(f"Order executed successfully: {result}")
        
        return result
        
    except ValidationError as e:
        self.logger.error(f"Order validation failed: {e}")
        raise
        
    except RiskError as e:
        self.logger.warning(f"Risk check failed: {e}")
        raise
        
    except ExchangeError as e:
        self.logger.error(f"Exchange error: {e}")
        # Retry logic could go here
        raise
        
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        raise TradingError(f"Trade execution failed: {e}") from e
```

## 📊 Performance Guidelines

### Optimization Principles
- **Profile First**: Measure before optimizing
- **Algorithm Choice**: Use appropriate data structures
- **Async Operations**: Use async/await for I/O operations
- **Caching**: Cache expensive computations
- **Lazy Loading**: Load data when needed

### Performance Examples
```python
# Good: Use async for I/O operations
async def fetch_multiple_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
    """Fetch multiple tickers concurrently."""
    tasks = [
        self.exchange.fetch_ticker(symbol) 
        for symbol in symbols
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return {
        symbol: result 
        for symbol, result in zip(symbols, results)
        if not isinstance(result, Exception)
    }

# Good: Cache expensive computations
from functools import lru_cache

@lru_cache(maxsize=128)
def calculate_technical_indicators(self, data: Tuple) -> Dict:
    """Calculate technical indicators with caching."""
    # Expensive calculation...
    pass

# Good: Use appropriate data structures
def find_correlated_positions(self, symbol: str, threshold: float) -> List[str]:
    """Find positions correlated above threshold."""
    correlations = self.position_correlations.get(symbol, {})
    return [
        pos for pos, corr in correlations.items() 
        if abs(corr) > threshold
    ]
```

## 🔒 Security Guidelines

### Security Principles
- **Input Validation**: Validate all inputs
- **Authentication**: Verify API credentials
- **Authorization**: Check permissions
- **Data Sanitization**: Clean user inputs
- **Secure Communication**: Use HTTPS/TLS
- **Secret Management**: Never hardcode secrets

### Security Examples
```python
import re
from urllib.parse import urlparse

def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format."""
    # Only allow alphanumeric and common separators
    pattern = r'^[A-Z0-9\-_]+$'
    return bool(re.match(pattern, symbol))

def validate_api_key(api_key: str) -> bool:
    """Validate API key format."""
    # Check length and format
    if len(api_key) < 32:
        return False
    
    # Check for common patterns
    if not re.match(r'^[a-zA-Z0-9]+$', api_key):
        return False
    
    return True

def sanitize_user_input(user_input: str) -> str:
    """Sanitize user input to prevent injection."""
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', '"', "'", '&', ';']
    for char in dangerous_chars:
        user_input = user_input.replace(char, '')
    
    return user_input.strip()
```

## 📈 Monitoring and Logging

### Logging Standards
```python
import logging
import json
from datetime import datetime

class StructuredLogger:
    """Structured logging for better monitoring."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
    
    def log_trade(self, action: str, details: Dict):
        """Log trade-related events."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "action": action,
            "details": details,
            "service": "trading"
        }
        
        self.logger.info(json.dumps(log_entry))
    
    def log_error(self, error: Exception, context: Dict = None):
        """Log error events."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "ERROR",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {},
            "service": "trading"
        }
        
        self.logger.error(json.dumps(log_entry))
```

### Metrics and Monitoring
```python
from prometheus_client import Counter, Histogram, Gauge

# Define metrics
TRADE_COUNTER = Counter('trades_total', 'Total trades executed', ['side', 'symbol'])
TRADE_DURATION = Histogram('trade_duration_seconds', 'Trade execution duration')
ACTIVE_POSITIONS = Gauge('active_positions', 'Number of active positions')

class TradingService:
    def __init__(self):
        self.trade_counter = TRADE_COUNTER
        self.trade_duration = TRADE_DURATION
        self.active_positions = ACTIVE_POSITIONS
    
    async def execute_order(self, order: Order) -> Dict:
        """Execute order with metrics."""
        start_time = time.time()
        
        try:
            result = await self._execute_order_internal(order)
            
            # Record metrics
            self.trade_counter.labels(
                side=order.side, 
                symbol=order.symbol
            ).inc()
            
            self.trade_duration.observe(time.time() - start_time)
            
            return result
            
        except Exception as e:
            # Record error metrics
            self.trade_counter.labels(
                side=order.side, 
                symbol=order.symbol
            ).inc()
            
            raise
```

## 🚀 Deployment Guidelines

### Environment Configuration
```bash
# Production environment
export ENVIRONMENT=production
export LOG_LEVEL=INFO
export DRY_RUN=false

# Development environment
export ENVIRONMENT=development
export LOG_LEVEL=DEBUG
export DRY_RUN=true

# Testing environment
export ENVIRONMENT=testing
export LOG_LEVEL=DEBUG
export DRY_RUN=true
```

### Health Checks
```python
class HealthChecker:
    """System health monitoring."""
    
    async def check_health(self) -> Dict[str, Any]:
        """Check system health status."""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        # Check exchange connectivity
        try:
            await self.exchange.ping()
            health_status["checks"]["exchange"] = "healthy"
        except Exception as e:
            health_status["checks"]["exchange"] = f"unhealthy: {e}"
            health_status["status"] = "unhealthy"
        
        # Check database connectivity
        try:
            await self.database.ping()
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = f"unhealthy: {e}"
            health_status["status"] = "unhealthy"
        
        return health_status
```

## 📋 Pull Request Checklist

### Before Submitting
- [ ] Code compiles without errors
- [ ] All tests pass
- [ ] Code quality checks pass (ruff, black, mypy)
- [ ] Documentation is updated
- [ ] No breaking changes (unless intentional)
- [ ] Performance impact considered
- [ ] Security implications reviewed

### PR Description Template
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Performance improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed
- [ ] All tests pass

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Code is self-documenting
- [ ] No hardcoded values
- [ ] Error handling is robust
- [ ] Logging is appropriate

## Related Issues
Closes #123
Related to #456
```

## 🆘 Getting Help

### Communication Channels
- **Issues**: GitHub Issues for bugs and feature requests
- **Discussions**: GitHub Discussions for questions and ideas
- **Pull Requests**: For code contributions
- **Documentation**: For usage questions

### Resources
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [pytest Documentation](https://docs.pytest.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Black Documentation](https://black.readthedocs.io/)
- [MyPy Documentation](https://mypy.readthedocs.io/)

---

**Next**: See [TESTING.md](TESTING.md) for testing guidelines, [ARCHITECTURE.md](ARCHITECTURE.md) for system design, or [README.md](README.md) for project overview.
