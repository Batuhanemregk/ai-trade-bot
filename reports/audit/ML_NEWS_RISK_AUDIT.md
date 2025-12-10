# ML / News / Risk Subsystem Audit Report
**Date:** 2025-12-09  
**Scope:** Static code analysis + architecture review  
**Status:** DRY-RUN / PAPER mode only

---

## 📊 Data Flow Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   OHLCV     │───▶│ FeatureBuilder │──▶│  ML Model   │───▶│  ML Score   │
│  (15m/1h)   │    │ (50+ features)  │  │ (LightGBM)  │    │  (0-100)    │
└─────────────┘    └─────────────────┘  └─────────────┘    └──────┬──────┘
                                                                  │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐             ▼
│ News APIs   │───▶│ DigestManager │──▶│ LLM Analyzer│───▶ ┌────────────┐
│ (CryptoPanic)│   │ (SHA256 hash) │   │ (GPT-4o-m)  │    │ Composite  │
└─────────────┘    └───────────────┘   └─────────────┘    │  Signal    │
                                                          │ (weights)  │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    └──────┬──────┘
│   TAScorer  │───▶│  Technical  │    │ RiskService │           │
│ (RSI,MACD..)│    │   Score     │───▶│ (5 metrics) │───▶ ┌────▼────────┐
└─────────────┘    └─────────────┘    └─────────────┘    │ SignalGate  │
                                                         │ Persist/Conf│
                                                         └──────┬──────┘
                                                                │
                                                         ┌──────▼──────┐
                                                         │ Protection  │
                                                         │   Guards    │
                                                         │ (once_per_  │
                                                         │  bar, cool) │
                                                         └──────┬──────┘
                                                                │
                                                         ┌──────▼──────┐
                                                         │   Execute   │
                                                         │ (OKX CCXT)  │
                                                         └─────────────┘
```

---

## 🔍 Findings

### ML Subsystem

| Severity | Type | Finding | Location |
|----------|------|---------|----------|
| ⚠️ Risk | Horizon | `forward_bars=3` (45min) at train, inference uses latest row | `ml/features/builder.py:366-392` |
| ✅ Good | Leakage | Label uses `shift(-forward_bars)`, no future data in features | `ml/features/builder.py:381` |
| ✅ Good | Split | TimeSeriesSplit (5-fold), no random shuffle | `ml/train_lightgbm.py:114` |
| ⚠️ Risk | Coin-based | 9 separate models (3 coins × 3 TF) - may overfit low samples | `scoring/ml_scorer.py:34-84` |
| 🔶 Smell | Fallback | Missing model → random 45-55 score, silent failure | `scoring/ml_scorer.py:273-301` |
| ❓ Open | Backtest | No offline backtest hook found | N/A |

### News Subsystem

| Severity | Type | Finding | Location |
|----------|------|---------|----------|
| ✅ Good | Digest | SHA256 hash on (url, timestamp, title), TTL=60min | `news_digest_manager.py:50-69` |
| ✅ Good | Watermark | Overlap fetch (30min) prevents gaps | `news_watermark_manager.py:72-79` |
| ⚠️ Risk | Budget | Daily token budget tracked, but no hard stop | `news_llm_analyzer.py:62-83` |
| 🔶 Smell | General | "general" news not assigned to any symbol | `news_service.py:349-419` |
| ✅ Good | Dedup | Merge by URL, sorted by timestamp | `news_service.py:275-289` |
| 🔶 Smell | Verbosity | LLM prompt ~800 tokens, could be shorter | `news_llm_analyzer.py:188-234` |

### Risk Subsystem

| Severity | Type | Finding | Location |
|----------|------|---------|----------|
| ⚠️ Risk | Leverage | No `max_leverage` enforcement at order time | Not found in code |
| ✅ Good | 5 Metrics | volatility, liquidity, correlation, score, market | `risk_service.py:22-76` |
| 🔶 Smell | Correlation | Tier-based static values, not real-time | `risk_service.py:257-292` |
| ⚠️ Bug | TP/SL | No OCO bracket found - TP/SL may not cancel each other | Not found |
| ✅ Good | Same-dir | `same_direction_block` prevents re-entry | `protection_guards.py:121-153` |
| ✅ Good | Once per bar | Prevents multiple entries in same bar | `protection_guards.py:52-84` |
| ⚠️ Risk | Reversal | Reversal closes opposite but no position check | `protection_guards.py:155-187` |

---

## 📋 Tut / Çıkar / Yeniden-İşle Tablosu

| Parameter | Current | Recommendation |
|-----------|---------|----------------|
| `NEWS_DIGEST_TTL_MIN` | 60 | **Tut** - reasonable cache |
| `LLM_VERBOSITY` | High (~800 tokens) | **Yeniden-İşle** - reduce to ~400 |
| `persist_bars` | 2 | **Tut** - good for noise filter |
| `confirm_bars` | 2 | **Tut** - prevents whipsaws |
| `forward_bars` | 3 (45min) | **Yeniden-İşle** - align with inference |
| `max_leverage` | Not enforced | **Ekle** - critical safety |
| `OCO_bracket` | Missing | **Ekle** - TP/SL must cancel each other |
| `correlation_guard` | Tier-static | **Yeniden-İşle** - use real correlation |
| `daily_budget_stop` | Soft limit | **Yeniden-İşle** - hard stop when exceeded |

---

## ✅ Checklist Answers

### ML
- **Label leakage?** NO - proper shift(-forward_bars)
- **Horizon consistent?** ⚠️ PARTIAL - 45min label, but inference unclear
- **Coin-based or shared?** Coin-based (9 models) - risk: low sample
- **Thresholds calibrated?** YES - CalibratedClassifierCV isotonic
- **Offline backtest hooks?** NO - not found

### News
- **Digest SAME/CHANGED overlap?** YES - works correctly
- **"general" symbol assignment?** NO - unassigned to any symbol
- **LLM verbosity & cache?** Cache OK, verbosity high
- **Rate-limit headers?** YES - tracked in prometheus

### Risk
- **Same-direction re-entry guard?** YES - active in protection_guards
- **Reverse signal flip?** YES - reversal manager exists
- **Correlation threshold applied?** PARTIAL - tier-based static values
- **Bracket OCO pairing?** NO - not found in codebase

---

## 🎯 Hemen Yap / Sonra / Vazgeç

### 🔥 Hemen Yap
1. Add `max_leverage` enforcement before order execution
2. Implement OCO bracket (TP/SL cancel each other)
3. Fix ML inference to align with 3-bar (45min) horizon

### 📅 Sonra
1. Reduce LLM prompt verbosity to save tokens
2. Assign "general" news to all symbols proportionally
3. Implement real-time correlation calculation
4. Add offline backtest hook for ML models

### 🚫 Vazgeç
1. Switching to global (shared) ML model - keep coin-based
2. Real-time news scraping - current API-based is sufficient
