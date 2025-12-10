# Bugs and Test Plan
**Date:** 2025-12-09  
**Scope:** ML, News, Risk subsystems

---

## 🐛 Top 10 Bugs

### 1. [CRITICAL] No OCO Bracket for TP/SL
**Location:** Not found in codebase  
**Repro:** Open position → TP triggers → SL still active (orphan order)  
**Expected:** TP triggers → SL cancelled automatically  
**Actual:** SL remains, may execute later causing double exit  

### 2. [HIGH] ML Horizon Mismatch
**Location:** `ml/features/builder.py:366-392`  
**Repro:** Train with `forward_bars=3` (45min), inference uses latest bar  
**Expected:** Inference should wait 45min after feature calculation  
**Actual:** Immediate inference may be premature  

### 3. [HIGH] No max_leverage Enforcement
**Location:** Not found  
**Repro:** Set `max_leverage=3` in policy.yaml → submit order with 10x  
**Expected:** Order rejected or leverage reduced  
**Actual:** Order executes with whatever leverage exchange allows  

### 4. [MEDIUM] "general" News Unassigned
**Location:** `application/news_service.py:349-419`  
**Repro:** Fetch news → "economy" or "regulation" articles → no symbol match  
**Expected:** Assign to all symbols proportionally  
**Actual:** Ignored, no score contribution  

### 5. [MEDIUM] LLM Budget Soft Limit
**Location:** `application/news_llm_analyzer.py:62-83`  
**Repro:** Exceed daily token budget  
**Expected:** Hard stop, return cached or neutral score  
**Actual:** Warning logged, continues calling API  

### 6. [MEDIUM] Correlation Guard Static Values
**Location:** `application/risk_service.py:257-292`  
**Repro:** Check correlation risk for BTC and ETH  
**Expected:** Real-time correlation calculation  
**Actual:** Static tier-based values (e.g., tier_1=25.0)  

### 7. [LOW] ML Fallback Silent Failure
**Location:** `scoring/ml_scorer.py:273-301`  
**Repro:** Missing model file for BTC_15m  
**Expected:** Clear error, use TA-only scoring  
**Actual:** Random 45-55 score with warning log  

### 8. [LOW] Reversal Without Position Check
**Location:** `application/protection_guards.py:155-187`  
**Repro:** Reversal signal with no open position  
**Expected:** Skip reversal logic  
**Actual:** May attempt to close non-existent position  

### 9. [LOW] News Digest TTL Race Condition
**Location:** `application/news_digest_manager.py:106-117`  
**Repro:** Concurrent requests near TTL expiry  
**Expected:** Atomic check-and-update  
**Actual:** Possible duplicate LLM calls  

### 10. [LOW] Feature Column Mismatch Warning
**Location:** `scoring/ml_scorer.py:152-160`  
**Repro:** Model trained with 60 features, inference has 55  
**Expected:** Pad missing features with 0 or median  
**Actual:** Warning logged, uses available features only  

---

## 🧪 Minimal Test Plan

### New Tests to Add

| File Path | Purpose | Priority |
|-----------|---------|----------|
| `tests/risk/test_reentry_guard.py` | Test same_direction_block prevents duplicate entry | HIGH |
| `tests/risk/test_bracket_oco.py` | Test TP/SL OCO pairing (once implemented) | HIGH |
| `tests/risk/test_leverage_limit.py` | Test max_leverage enforcement | HIGH |
| `tests/ml/test_horizon_consistency.py` | Test ML inference timing vs training horizon | MEDIUM |
| `tests/news/test_general_news_assignment.py` | Test "general" news assigned to all symbols | MEDIUM |

### Test Stubs

```python
# tests/risk/test_reentry_guard.py
import pytest
from application.protection_guards import ProtectionGuards

def test_same_direction_block_prevents_duplicate_long():
    """LONG position exists → new LONG signal blocked"""
    guards = ProtectionGuards()
    positions = {"BTC-USDT-SWAP": {"side": "long", "size": 0.1}}
    result = guards.check_same_direction_block("BTC-USDT-SWAP", "LONG", positions)
    assert not result.allowed
    assert "same_direction" in result.reason

def test_same_direction_block_allows_reversal():
    """LONG position exists → SHORT signal allowed (reversal)"""
    guards = ProtectionGuards()
    positions = {"BTC-USDT-SWAP": {"side": "long", "size": 0.1}}
    result = guards.check_same_direction_block("BTC-USDT-SWAP", "SHORT", positions)
    assert result.allowed
```

```python
# tests/risk/test_leverage_limit.py
import pytest

def test_leverage_limit_enforced():
    """Order with leverage > max_leverage rejected"""
    # TODO: Implement once leverage enforcement added
    pass

def test_leverage_within_limit_allowed():
    """Order with leverage <= max_leverage accepted"""
    pass
```

```python
# tests/ml/test_horizon_consistency.py
import pytest
from ml.features.builder import FeatureBuilder

def test_label_horizon_matches_documentation():
    """forward_bars=3 means 45min at 15m TF"""
    builder = FeatureBuilder()
    # Verify label creation uses correct horizon
    assert True  # placeholder
```

---

## 🛡️ Safety Rails

### Duplicate Entry Prevention
- [x] `once_per_bar` guard active (`protection_guards.py:52-84`)
- [x] `same_direction_block` active (`protection_guards.py:121-153`)
- [x] `entry_cooldown` active (`protection_guards.py:86-119`)

### Bracket Protection
- [ ] **MISSING:** OCO bracket (TP cancels SL and vice versa)
- [ ] **MISSING:** Orphan order cleanup job

### Same Direction Re-entry
- [x] Blocked by `same_direction_block` when position exists
- [ ] **MISSING:** Cooldown after partial close

---

## 📊 Coverage Gaps

| Area | Existing Tests | Missing Tests |
|------|----------------|---------------|
| ML Scorer | `test_ml_news_fallbacks.py` | horizon consistency, feature mismatch |
| News Digest | None | TTL expiry, SAME/CHANGED logic |
| Risk Service | `test_risk_service.py` | leverage limit, correlation real-time |
| Protection | None | re-entry guard, once_per_bar edge cases |
| Signal Gate | `test_scoring_consistency.py` | hysteresis boundary conditions |
