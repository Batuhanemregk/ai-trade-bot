# 🧪 Testing Guide

> **Comprehensive Testing Strategy and Execution**

## 🎯 Overview

AiBotBS implements a comprehensive testing strategy with multiple test layers, offline determinism, and automated quality gates. The testing framework ensures code quality, prevents regressions, and maintains system reliability.

## 🏗️ Testing Architecture

### Test Layers
```
┌─────────────────────────────────────────────────────────────┐
│                    Production Code                          │
├─────────────────────────────────────────────────────────────┤
│                    Integration Tests                        │
│                 (Glue Layer Tests)                         │
├─────────────────────────────────────────────────────────────┤
│                     Unit Tests                              │
│                  (Core Layer Tests)                        │
├─────────────────────────────────────────────────────────────┤
│                    Test Fixtures                            │
│              (Offline, Deterministic)                      │
└─────────────────────────────────────────────────────────────┘
```

### Test Categories

#### 1. **Core Tests** (`pytest -m "core"`)
- Unit tests for individual components
- Fast execution (< 1 second per test)
- No external dependencies
- Pure function testing

#### 2. **Glue Tests** (`pytest -m "glue"`)
- Integration tests between modules
- Tests complete workflows
- Uses offline fixtures
- Moderate execution time

#### 3. **Smoke Tests** (`scripts/ci_smoke.sh`)
- End-to-end system validation
- Critical path verification
- Fast feedback loop
- CI/CD integration

## 🚀 Quick Start

### Basic Test Execution
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/core/test_scoring.py

# Run specific test function
pytest tests/core/test_scoring.py::test_ml_scorer
```

### Test Categories
```bash
# Core tests only (fast)
pytest -m "core"

# Glue tests only (integration)
pytest -m "glue"

# Both core and glue
pytest -m "core or glue"

# Exclude slow tests
pytest -m "not slow"
```

### CI Smoke Test
```bash
# Run smoke test suite
bash scripts/ci_smoke.sh

# Run with verbose output
bash scripts/ci_smoke.sh --verbose
```

## 📁 Test Structure

### Directory Layout
```
tests/
├── __init__.py
├── conftest.py                 # Global fixtures
├── fixtures/                   # Test fixtures
│   ├── __init__.py
│   └── common.py              # Common offline fixtures
├── core/                       # Core unit tests
│   ├── __init__.py
│   ├── test_scoring.py
│   ├── test_risk.py
│   ├── test_execution.py
│   └── test_telegram.py
├── glue/                       # Integration tests
│   ├── __init__.py
│   ├── test_trade_service_flow.py
│   ├── test_telegram_commands.py
│   └── test_scheduler_jobs.py
└── integration/                # End-to-end tests
    ├── __init__.py
    └── test_full_workflow.py
```

### Test File Naming Convention
- `test_*.py` - Test files
- `test_*_flow.py` - Integration workflow tests
- `test_*_commands.py` - Command/API tests
- `test_*_service.py` - Service layer tests

## 🧩 Test Fixtures

### Common Fixtures (`tests/fixtures/common.py`)

#### `FakeExchange`
Offline, deterministic exchange simulator for testing.

```python
import pytest
from tests.fixtures.common import FakeExchange

def test_order_creation(fake_exchange):
    # Create a test order
    order = await fake_exchange.create_order(
        symbol="BTC-USDT",
        type="market",
        side="buy",
        amount=0.1
    )
    
    assert order["status"] == "closed"
    assert order["filled"] == 0.1
```

#### `FakeREST`
Offline REST API simulator for bracket order testing.

```python
def test_bracket_orders(fake_rest):
    # Test bracket order creation
    result = await fake_rest.create_order(
        symbol="BTC-USDT",
        type="stop",
        side="sell",
        amount=0.1,
        price=50000
    )
    
    assert result["status"] == "open"
```

#### `env_isolation`
Isolated environment for test isolation.

```python
def test_with_isolated_env(env_isolation):
    # Environment is isolated from system
    os.environ["TEST_VAR"] = "test_value"
    
    # Test runs in isolation
    assert os.environ["TEST_VAR"] == "test_value"
```

#### `mock_policy`
Mock trading policy for testing.

```python
def test_with_mock_policy(mock_policy):
    # Policy is mocked for testing
    assert mock_policy["risk"]["max_daily_loss"] == 0.05
    assert mock_policy["scoring"]["min_score"] == 0.5
```

### Fixture Usage
```python
import pytest

@pytest.mark.asyncio
async def test_trade_flow(fake_exchange, fake_rest, mock_policy):
    # Use multiple fixtures
    service = TradeService(
        exchange=fake_exchange,
        policy=mock_policy,
        risk_service=MockRiskService()
    )
    
    result = await service.execute_signal(
        symbol="BTC-USDT",
        side="buy",
        qty=0.1,
        price=50000
    )
    
    assert result["status"] == "success"
```

## 🏷️ Test Markers

### Built-in Markers

#### `@pytest.mark.core`
Marks tests as core unit tests.

```python
import pytest

@pytest.mark.core
def test_ml_scorer():
    """Test ML scoring function."""
    result = ml_scorer(sample_data)
    assert 0 <= result <= 1
```

#### `@pytest.mark.glue`
Marks tests as integration tests.

```python
@pytest.mark.glue
@pytest.mark.asyncio
async def test_trade_service_flow():
    """Test complete trade service workflow."""
    # Integration test logic
    pass
```

#### `@pytest.mark.slow`
Marks slow-running tests.

```python
@pytest.mark.slow
def test_large_dataset():
    """Test with large dataset (slow)."""
    # Slow test logic
    pass
```

#### `@pytest.mark.asyncio`
Marks asynchronous tests.

```python
@pytest.mark.asyncio
async def test_async_function():
    """Test asynchronous function."""
    result = await async_function()
    assert result is not None
```

### Custom Markers
```python
# pytest.ini
[tool:pytest]
markers =
    core: Core unit tests
    glue: Integration tests
    slow: Slow-running tests
    asyncio: Asynchronous tests
    offline: Offline-only tests
    online: Online-required tests
```

## 🔄 Test Execution Patterns

### Sequential Execution
```bash
# Run tests sequentially
pytest --tb=short

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test pattern
pytest -k "test_order"
```

### Parallel Execution
```bash
# Run tests in parallel (if pytest-xdist installed)
pytest -n auto

# Run with specific number of workers
pytest -n 4

# Parallel with coverage
pytest -n auto --cov=. --cov-report=html
```

### Test Discovery
```bash
# Discover tests without running
pytest --collect-only

# Show test collection errors
pytest --collect-only -q

# List test markers
pytest --markers
```

## 📊 Test Coverage

### Coverage Configuration
```ini
# .coveragerc
[run]
source = .
omit = 
    */tests/*
    */venv/*
    */__pycache__/*
    setup.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod
```

### Coverage Reports
```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Generate XML coverage report
pytest --cov=. --cov-report=xml

# Generate terminal coverage report
pytest --cov=. --cov-report=term-missing
```

### Coverage Targets
```bash
# Fail if coverage below threshold
pytest --cov=. --cov-fail-under=80

# Show missing lines
pytest --cov=. --cov-report=term-missing
```

## 🚨 Error Handling Tests

### Exception Testing
```python
import pytest

def test_invalid_input():
    """Test that invalid input raises appropriate exception."""
    with pytest.raises(ValueError, match="Invalid symbol"):
        validate_symbol("")

def test_custom_exception():
    """Test custom exception types."""
    with pytest.raises(TradingError, match="Insufficient balance"):
        execute_trade(symbol="BTC-USDT", amount=1000000)
```

### Async Exception Testing
```python
@pytest.mark.asyncio
async def test_async_exception():
    """Test async exception handling."""
    with pytest.raises(ConnectionError):
        await async_function_that_fails()
```

## 🔧 Test Configuration

### pytest Configuration
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    core: Core unit tests
    glue: Integration tests
    slow: Slow-running tests
    asyncio: Asynchronous tests
```

### Environment Configuration
```bash
# .env.test
TESTING=true
DRY_RUN=true
LOG_LEVEL=DEBUG
AIBOTBS_STATE_DIR=test_state
AIBOTBS_LOG_DIR=test_logs
```

## 🧪 Offline Testing Rules

### Deterministic Mocks
```python
# Always use deterministic fixtures
def test_with_deterministic_data(fake_exchange, mock_policy):
    # Results should be consistent across runs
    result1 = await function_under_test(fake_exchange, mock_policy)
    result2 = await function_under_test(fake_exchange, mock_policy)
    
    assert result1 == result2
```

### No External Dependencies
```python
# Never make real API calls in tests
@pytest.mark.offline
def test_no_external_calls(fake_exchange):
    # Use fake exchange, never real API
    result = await fake_exchange.fetch_ticker("BTC-USDT")
    assert result["symbol"] == "BTC-USDT"
```

### Time-Independent Tests
```python
# Use frozen time for time-dependent tests
from freezegun import freeze_time

@freeze_time("2024-01-01 12:00:00")
def test_time_independent():
    """Test that doesn't depend on current time."""
    current_time = datetime.now()
    assert current_time.year == 2024
```

## 🔍 Debugging Tests

### Verbose Output
```bash
# Show detailed test output
pytest -v -s

# Show local variables on failure
pytest --tb=long

# Show captured output
pytest -s
```

### Test Isolation
```bash
# Run single test in isolation
pytest tests/core/test_scoring.py::test_ml_scorer -v -s

# Run with specific markers only
pytest -m "core" -v -s
```

### Debugging Failed Tests
```python
import pytest

def test_with_debugging():
    """Test with debugging information."""
    # Add breakpoint for debugging
    breakpoint()
    
    result = function_under_test()
    assert result is not None
```

## 📈 Performance Testing

### Benchmark Tests
```python
import pytest
import time

@pytest.mark.benchmark
def test_performance():
    """Test function performance."""
    start_time = time.time()
    
    # Function under test
    result = expensive_function()
    
    execution_time = time.time() - start_time
    
    # Assert performance requirements
    assert execution_time < 1.0  # Must complete within 1 second
    assert result is not None
```

### Load Testing
```python
@pytest.mark.load
@pytest.mark.asyncio
async def test_concurrent_execution():
    """Test concurrent execution performance."""
    import asyncio
    
    # Create multiple concurrent tasks
    tasks = [
        async_function() for _ in range(100)
    ]
    
    start_time = time.time()
    results = await asyncio.gather(*tasks)
    execution_time = time.time() - start_time
    
    # Assert concurrent performance
    assert execution_time < 5.0  # Must complete within 5 seconds
    assert len(results) == 100
```

## 🚀 CI/CD Integration

### GitHub Actions
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: |
          python -m compileall .
          bash scripts/ci_smoke.sh
          pytest -m "core or glue" --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Local CI Simulation
```bash
# Simulate CI locally
bash scripts/ci_all.sh

# Run specific CI steps
bash scripts/ci_smoke.sh
bash scripts/ci_tests.sh
bash scripts/ci_lint.sh
```

## 🔧 Test Maintenance

### Test Data Management
```python
# Use factories for test data
from tests.factories import OrderFactory, TradeFactory

def test_with_factory_data():
    """Test using factory-generated data."""
    order = OrderFactory.create(side="buy", amount=0.1)
    trade = TradeFactory.create(order=order)
    
    assert trade.order_id == order.id
    assert trade.side == "buy"
```

### Test Cleanup
```python
import pytest

@pytest.fixture(autouse=True)
def cleanup():
    """Automatic cleanup after each test."""
    yield
    # Cleanup code here
    cleanup_test_data()
    reset_mocks()
```

### Test Documentation
```python
def test_complex_workflow():
    """
    Test complex trading workflow.
    
    This test verifies the complete flow from signal generation
    to order execution and position management.
    
    Steps:
    1. Generate trading signal
    2. Validate signal with risk service
    3. Execute entry order
    4. Attach bracket orders (TP/SL)
    5. Verify position creation
    
    Expected: Complete workflow success with proper order states.
    """
    # Test implementation
    pass
```

## 🚨 Common Test Issues

### 1. **Import Errors**
**Problem**: `ModuleNotFoundError` or `ImportError`
**Solution**: Check `PYTHONPATH` and import paths

```bash
export PYTHONPATH=$PWD
python -m pytest
```

### 2. **Fixture Not Found**
**Problem**: `FixtureNotFoundError`
**Solution**: Ensure fixtures are properly imported in `conftest.py`

```python
# conftest.py
from tests.fixtures.common import *

pytest_plugins = ["tests.fixtures.common"]
```

### 3. **Async Test Failures**
**Problem**: `RuntimeError: Event loop is closed`
**Solution**: Use `@pytest.mark.asyncio` and proper async setup

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### 4. **Test Isolation Issues**
**Problem**: Tests affecting each other
**Solution**: Use proper fixtures and cleanup

```python
@pytest.fixture(autouse=True)
def isolate_test():
    # Setup isolation
    yield
    # Cleanup isolation
```

## 📚 Testing Best Practices

### 1. **Test Naming**
- Use descriptive test names
- Follow pattern: `test_<function>_<scenario>_<expected>`
- Example: `test_execute_signal_with_valid_params_returns_success`

### 2. **Test Structure**
- Arrange: Set up test data and conditions
- Act: Execute function under test
- Assert: Verify expected outcomes

### 3. **Test Independence**
- Each test should be independent
- No shared state between tests
- Use fresh fixtures for each test

### 4. **Test Coverage**
- Aim for >80% code coverage
- Test happy path and edge cases
- Test error conditions and exceptions

### 5. **Performance**
- Keep tests fast (< 1 second for unit tests)
- Use appropriate markers for slow tests
- Parallelize when possible

---

**Next**: See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, [ARCHITECTURE.md](ARCHITECTURE.md) for system design, or [EXECUTION.md](EXECUTION.md) for execution testing.
