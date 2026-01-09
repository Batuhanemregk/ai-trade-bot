# AI Trade Bot - Detailed Flow Diagrams

> All diagrams use ASCII-only characters for maximum compatibility.

---

## 1. System Architecture Overview

```mermaid
graph TB
    subgraph EntryPoints[Entry Points]
        A[run_live.ps1] --> B[main.py]
        B --> C[infrastructure/runtime.py]
    end

    subgraph Scheduler[Scheduler Layer]
        C --> D[SchedulerRunner]
        D --> E[APScheduler]
        E --> F1[trading_15m]
        E --> F2[trailing_5m]
        E --> F3[regime_1h]
        E --> F4[risk_1m]
    end

    subgraph Jobs[Analysis Jobs]
        F1 --> G1[TradingAnalysisJob]
        F2 --> G2[Trailing5mJob]
        F3 --> G3[Regime1hJob]
        F4 --> G4[RiskMonitorJob]
    end

    subgraph State[Shared State]
        H1[(policy.yaml)]
        H2[(runtime_state.json)]
        H3[(position_states.json)]
    end

    subgraph Telegram[Telegram UI]
        I1[TelegramBot]
        I2[Handlers]
        I3[Notifications]
    end
```

---

## 2. Main Trading Pipeline (15-Minute Cycle)

```mermaid
flowchart TD
    START([Every 15 minutes]) --> INIT

    subgraph INIT[1. Initialization]
        A1[Load policy.yaml] --> A2[Create exchange adapter]
        A2 --> A3[Get coin list]
    end

    INIT --> FETCH

    subgraph FETCH[2. Data Fetching]
        C1[15m OHLCV 200 bars] --> C2[1h OHLCV 200 bars]
        C2 --> C3[4h OHLCV 200 bars]
        C3 --> C4{Enough data? min 50 bars}
        C4 -->|No| SKIP1([Skip to next coin])
        C4 -->|Yes| NEXT1[Continue]
    end

    NEXT1 --> SCORING

    subgraph SCORING[3. Scoring]
        D1[TAScorer.score - 50%] --> D5[All Scores]
        D2[MLScorer.score - 40%] --> D5
        D3[NewsScorer.score - 5%] --> D5
        D4[RiskService - 5%] --> D5
    end

    SCORING --> COMPOSITE

    subgraph COMPOSITE[4. Composite Score]
        E1{ML score is None?}
        E1 -->|Yes| E2[Redistribute ML weight to TA]
        E1 -->|No| E3[Use normal weights]
        E2 --> E4[Calculate final score]
        E3 --> E4
        E4 --> E5[Assign Grade A+/A/B/C/D]
    end

    COMPOSITE --> DECISION

    subgraph DECISION[5. Decision]
        F1{Score >= 63?}
        F1 -->|Yes| F2[LONG]
        F1 -->|No| F3{Score <= 30?}
        F3 -->|Yes| F4[SHORT]
        F3 -->|No| F5[FLAT]
    end

    DECISION --> GATE

    subgraph GATE[6. Signal Gate]
        G1[Persistence: 2 bars same direction] --> G2[Confirmation: 2 bars for reversal]
        G2 --> G3{ADX >= 22?}
        G3 -->|Yes| G4[PASS - Valid signal]
        G3 -->|No| G5[PENDING - Wait]
    end

    G5 --> SKIP1
    G4 --> STATE

    subgraph STATE[7. State Machine]
        H1{Current state?}
        H1 -->|READY| H2[Transition: OPEN_LONG or OPEN_SHORT]
        H1 -->|LONG_OPEN| H3{Signal direction?}
        H3 -->|SHORT| H4[Transition: REVERSE]
        H3 -->|LONG| H5[Transition: IGNORE]
        H1 -->|SHORT_OPEN| H6{Signal direction?}
        H6 -->|LONG| H7[Transition: REVERSE]
        H6 -->|SHORT| H8[Transition: IGNORE]
        H1 -->|COOLDOWN| H9{Time elapsed?}
        H9 -->|Yes| H10[State: READY]
        H9 -->|No| H11[MAINTAIN]
    end

    H2 --> EXECUTE
    H4 --> EXECUTE
    H7 --> EXECUTE

    subgraph EXECUTE[8. Trade Execution]
        I1[Calculate position size] --> I2[Apply leverage]
        I2 --> I3[Send market order]
        I3 --> I4[Create OCO bracket TP + SL]
    end

    EXECUTE --> NOTIFY[Telegram Notification]
```

---

## 3. Trade Execution Detail

```mermaid
flowchart TD
    START([_execute_trade starts]) --> CHECK1

    subgraph CHECK1[1. Pre-checks]
        A1{Trading paused?}
        A1 -->|Yes| SKIP1([Skip])
        A1 -->|No| A2[Protection guards check]
        A2 --> A3{All guards OK?}
        A3 -->|No| SKIP2([Skip + Log])
        A3 -->|Yes| A4[Determine mode: LIVE/PAPER/DRY-RUN]
    end

    A4 --> PRICE

    subgraph PRICE[2. Price and Size]
        B1[Fetch current price] --> B2[Calculate position size]
        B2 --> B3[Tier-based sizing]
        B3 --> B4[Apply leverage: notional = margin x leverage]
        B4 --> B5[Calculate contracts: contracts = notional / price]
    end

    PRICE --> VALIDATE

    subgraph VALIDATE[3. Validation]
        C1[ensure_minimums: Min lot, min notional] --> C2{Meets minimum?}
        C2 -->|No| C3[Bump to minimum]
        C2 -->|Yes| C4[Continue]
        C3 --> C4
        C4 --> C5[quantize_price: Round to tick size]
        C5 --> C6[quantize_size: Round to lot size]
    end

    VALIDATE --> TPSL

    subgraph TPSL[4. TP/SL Calculation]
        D1[Calculate ATR 14 periods] --> D2{ATR valid?}
        D2 -->|Yes| D3[SL = Entry +/- 4xATR, TP = Entry +/- 6xATR]
        D2 -->|No| D4[SL = Entry +/- 1.5%, TP = Entry +/- 3.0%]
        D3 --> D5[validate_bracket_order]
        D4 --> D5
    end

    TPSL --> ORDER

    subgraph ORDER[5. Order Submission]
        E1{Mode?}
        E1 -->|LIVE| E2[Set leverage on OKX]
        E2 --> E3[create_market_order via CCXT]
        E3 --> E4{Success?}
        E4 -->|No| ERROR1([Order failed])
        E4 -->|Yes| E5[Update balance tracker]

        E1 -->|PAPER| E6[PaperExecutor: Virtual order]
        E6 --> E7[Create virtual position]

        E1 -->|DRY-RUN| E8[Log only]
    end

    E5 --> BRACKET
    E7 --> BRACKET

    subgraph BRACKET[6. OCO Bracket]
        F1{Mode?}
        F1 -->|LIVE| F2[_create_oco_bracket]
        F2 --> F3[TP trigger order via OKX algo]
        F3 --> F4[SL trigger order via OKX algo]
        F4 --> F5[Create OCO link]

        F1 -->|PAPER| F6[Virtual bracket orders]
    end

    BRACKET --> UPDATE

    subgraph UPDATE[7. State Update]
        G1[get_state_manager] --> G2[process_signal]
        G2 --> G3[State: READY to OPEN]
        G3 --> G4{Is reversal?}
        G4 -->|Yes| G5[Send Telegram reversal notification]
        G4 -->|No| G6[Log only]
    end

    UPDATE --> END1([Trade completed])
```

---

## 4. Exit Strategies (5-Minute Cycle)

```mermaid
flowchart TD
    START([Every 5 minutes]) --> INIT

    subgraph INIT[1. Initialize]
        A1[Get exchange adapter] --> A2[Fetch active positions]
        A2 --> A3{Any positions?}
        A3 -->|No| END1([Nothing to do])
        A3 -->|Yes| LOOP
    end

    subgraph LOOP[2. For Each Position]
        B1[Select position] --> B2[Fetch current price]
        B2 --> B3[Calculate R-multiple: R = PnL / Risk]
    end

    LOOP --> TRAILING

    subgraph TRAILING[3. Trailing Stop]
        C1{Trailing enabled?}
        C1 -->|No| PARTIAL
        C1 -->|Yes| C2{R >= 0.5? Activation}
        C2 -->|No| C3[Trailing not active yet]
        C2 -->|Yes| C4{R >= 1.0? Breakeven}
        C4 -->|No| C5[Normal trailing: 2% offset]
        C4 -->|Yes| C6{R >= 1.5? Tight}
        C6 -->|No| C7[Breakeven: SL = Entry]
        C6 -->|Yes| C8[Tight trailing: 0.3% offset]
        C5 --> C9[Calculate new SL]
        C7 --> C9
        C8 --> C9
        C9 --> C10{New SL > Old SL?}
        C10 -->|Yes| C11[Update SL on OKX]
        C10 -->|No| C12[No update]
    end

    C3 --> PARTIAL
    C11 --> PARTIAL
    C12 --> PARTIAL

    subgraph PARTIAL[4. Partial Take Profit]
        D1{Partial TP enabled?}
        D1 -->|No| TIMEEXIT
        D1 -->|Yes| D2{R >= 1.0? Level 1}
        D2 -->|No| TIMEEXIT
        D2 -->|Yes| D3{Level 1 taken?}
        D3 -->|No| D5[Close 33%]
        D3 -->|Yes| D4{R >= 2.0? Level 2}
        D4 -->|No| TIMEEXIT
        D4 -->|Yes| D6{Level 2 taken?}
        D6 -->|No| D8[Close 33%]
        D6 -->|Yes| D7{R >= 4.0? Level 3}
        D7 -->|No| TIMEEXIT
        D7 -->|Yes| D9{Level 3 taken?}
        D9 -->|No| D10[Close 34% - Full exit]
        D9 -->|Yes| TIMEEXIT
        D5 --> D11[Market order to close]
        D8 --> D11
        D10 --> D11
    end

    D11 --> TIMEEXIT

    subgraph TIMEEXIT[5. Time-Based Exit]
        E1{Time exit enabled?}
        E1 -->|No| NEXT
        E1 -->|Yes| E2[Calculate position age]
        E2 --> E3{Age >= 24 hours?}
        E3 -->|No| E4{Age >= 20 hours?}
        E4 -->|Yes| E5[Log warning]
        E4 -->|No| NEXT
        E3 -->|Yes| E6[Force close entire position]
    end

    E5 --> NEXT
    E6 --> NEXT

    NEXT[Next position] --> B1
```

---

## 5. ML Scoring Pipeline

```mermaid
flowchart TD
    START([MLScorer.score starts]) --> EXTRACT

    subgraph EXTRACT[1. Symbol Extraction]
        A1[Parse symbol: BTC-USDT-SWAP to BTC] --> A2[Determine timeframe: Default 15m]
        A2 --> A3[Create model key: BTC_15m]
    end

    EXTRACT --> LOOKUP

    subgraph LOOKUP[2. Model Lookup]
        B1{Model loaded?}
        B1 -->|No| B2[_fallback_score: Return None]
        B1 -->|Yes| B3[Get model]
        B2 --> END1([TA-only mode])
    end

    B3 --> FEATURES

    subgraph FEATURES[3. Feature Engineering]
        C1[Get OHLCV bundle: main, 1h, 4h] --> C2[FeatureBuilder.build_features]
        C2 --> C3[Technical indicators: RSI, MACD, BB, ATR, ADX]
        C3 --> C4[MTF features from 1h and 4h]
        C4 --> C5[Get feature_columns from metadata]
        C5 --> C6{All features available?}
        C6 -->|No| C7[Log missing features]
        C6 -->|Yes| C8[DataFrame ready]
        C7 --> C8
    end

    C8 --> PREDICT

    subgraph PREDICT[4. Prediction]
        D1[Get last bar features] --> D2{NaN or Inf values?}
        D2 -->|Yes| D3[_fallback_score]
        D2 -->|No| D4[model.predict_proba]
        D4 --> D5{Model type?}
        D5 -->|Multi-class| D6[3 classes: DOWN, NEUTRAL, UP]
        D5 -->|Binary| D7[2 classes: DOWN, UP]
    end

    D3 --> END2([TA-only mode])

    D6 --> SCORE_MULTI
    D7 --> SCORE_BINARY

    subgraph SCORE_MULTI[5a. Multi-class Scoring]
        E1[Get p_down, p_neutral, p_up] --> E2[net_bullish = p_up - p_down]
        E2 --> E3[ml_score = 50 + net_bullish x 50]
        E3 --> E4[Clamp 0-100]
    end

    subgraph SCORE_BINARY[5b. Binary Scoring]
        F1[Get p_up] --> F2{p_up >= 0.70?}
        F2 -->|Yes| F3[score = 70-100, LONG]
        F2 -->|No| F4{p_up >= 0.55?}
        F4 -->|Yes| F5[score = 60-70, LONG_WEAK]
        F4 -->|No| F6{p_up >= 0.45?}
        F6 -->|Yes| F7[score = 40-60, NEUTRAL]
        F6 -->|No| F8{p_up >= 0.30?}
        F8 -->|Yes| F9[score = 20-40, SHORT_WEAK]
        F8 -->|No| F10[score = 0-20, SHORT]
    end

    SCORE_MULTI --> DIRECTION
    F3 --> DIRECTION
    F5 --> DIRECTION
    F7 --> DIRECTION
    F9 --> DIRECTION
    F10 --> DIRECTION

    subgraph DIRECTION[6. Direction and Confidence]
        G1{score >= 65?}
        G1 -->|Yes| G2[LONG]
        G1 -->|No| G3{score >= 55?}
        G3 -->|Yes| G4[LONG_WEAK]
        G3 -->|No| G5{score >= 45?}
        G5 -->|Yes| G6[NEUTRAL]
        G5 -->|No| G7{score >= 35?}
        G7 -->|Yes| G8[SHORT_WEAK]
        G7 -->|No| G9[SHORT]

        G2 --> G10[Calculate confidence]
        G4 --> G10
        G6 --> G10
        G8 --> G10
        G9 --> G10
    end

    G10 --> RETURN([Return: score, rationale, details])
```

---

## 6. Composite Signal Calculation

```mermaid
flowchart TD
    START([_compute_composite_signal]) --> BLOCKS

    subgraph BLOCKS[1. Create Blocks]
        A1[TechnicalBlock: score, rationale, flags] --> A2[MLBlock: score or None, rationale, details]
        A2 --> A3[NewsBlock: score, categories, rationale, volatility]
        A3 --> A4[RiskBlock: score, details]
    end

    BLOCKS --> WEIGHTS

    subgraph WEIGHTS[2. Load Weights]
        B1[Read from policy.yaml] --> B2[ta_weight: 0.50]
        B2 --> B3[ml_weight: 0.40]
        B3 --> B4[news_weight: 0.05]
        B4 --> B5[risk_weight: 0.05]
    end

    WEIGHTS --> MLCHECK

    subgraph MLCHECK[3. ML Check]
        C1{ml_score is None?}
        C1 -->|Yes| C2[Transfer ML weight to TA: effective_ta = 0.90]
        C1 -->|No| C3[Use normal weights]
        C2 --> C4[TA-only calculation]
        C3 --> BOOST
    end

    subgraph BOOST[4. ML Boost - Optional]
        D1{ML Boost enabled?}
        D1 -->|No| D2[Normal calculation]
        D1 -->|Yes| D3[Check tiers]
        D3 --> D4{TA >= 70?}
        D4 -->|Yes| D5[ML x 4]
        D4 -->|No| D6{TA >= 65?}
        D6 -->|Yes| D7[ML x 5]
        D6 -->|No| D8{TA >= 60?}
        D8 -->|Yes| D9[ML x 3]
        D8 -->|No| D2
        D5 --> D10[Boosted ML score]
        D7 --> D10
        D9 --> D10
    end

    D2 --> CALC
    D10 --> CALC
    C4 --> GRADE

    subgraph CALC[5. Final Score Calculation]
        E1[final_score = ta_w x TA + ml_w x ML + news_w x News + risk_w x Risk]
    end

    CALC --> GRADE

    subgraph GRADE[6. Grade Assignment]
        F1{score >= 90?}
        F1 -->|Yes| F2[Grade: A+]
        F1 -->|No| F3{score >= 80?}
        F3 -->|Yes| F4[Grade: A]
        F3 -->|No| F5{score >= 70?}
        F5 -->|Yes| F6[Grade: B]
        F5 -->|No| F7{score >= 60?}
        F7 -->|Yes| F8[Grade: C]
        F7 -->|No| F9[Grade: D]
    end

    F2 --> DECISION
    F4 --> DECISION
    F6 --> DECISION
    F8 --> DECISION
    F9 --> DECISION

    subgraph DECISION[7. Decision]
        G1{score >= 63?}
        G1 -->|Yes| G2[LONG]
        G1 -->|No| G3{score <= 30?}
        G3 -->|Yes| G4[SHORT]
        G3 -->|No| G5[FLAT]
    end

    G2 --> RETURN
    G4 --> RETURN
    G5 --> RETURN

    RETURN([Return CompositeSignal])
```

---

## 7. Signal Gate Processing

```mermaid
flowchart TD
    START([SignalGate.process_signal]) --> PERSIST

    subgraph PERSIST[1. Persistence Check]
        A1[Get last N bars history] --> A2[Count bars in same direction]
        A2 --> A3{count >= persistence_bars? Default: 2}
        A3 -->|No| A4[is_valid: false, reason: Persistence not met]
        A3 -->|Yes| A5[Persistence OK]
    end

    A4 --> RETURN_INVALID
    A5 --> CONFIRM

    subgraph CONFIRM[2. Confirmation Check]
        B1{Is reversal?}
        B1 -->|No| B2[Skip confirmation]
        B1 -->|Yes| B3[Check last rev_confirm_bars]
        B3 --> B4{New direction for confirm_bars? Default: 2}
        B4 -->|No| B5[is_valid: false, reason: Reversal not confirmed]
        B4 -->|Yes| B6[Confirmation OK]
    end

    B2 --> REGIME
    B5 --> RETURN_INVALID
    B6 --> REGIME

    subgraph REGIME[3. Regime Check]
        C1[Calculate ADX from 1h OHLCV] --> C2{ADX >= adx_1h_min? Default: 22}
        C2 -->|No| C3[regime: RANGE, confidence_mult: 0.7]
        C2 -->|Yes| C4[regime: TREND, confidence_mult: 1.0]
        C3 --> C5{Trend throttle?}
        C5 -->|Yes| C6[trend_throttle: true]
        C5 -->|No| C7[Normal processing]
    end

    C6 --> HYSTERESIS
    C7 --> HYSTERESIS
    C4 --> HYSTERESIS

    subgraph HYSTERESIS[4. Hysteresis]
        D1[Get previous score] --> D2{Score change?}
        D2 -->|Less than margin| D3[Use previous score]
        D2 -->|Greater than margin| D4[Use new score]
        D3 --> D5[Calculate gated_score]
        D4 --> D5
    end

    HYSTERESIS --> FINAL

    subgraph FINAL[5. Final Decision]
        E1[Create GatedSignal] --> E2[Set: original_score, gated_score, direction, strength, is_valid, reason, regime_info]
    end

    FINAL --> RETURN_VALID([Return GatedSignal])
    RETURN_INVALID([Return Invalid GatedSignal])
```

---

## Quick Reference

| Flow            | Trigger         | Main File           | Key Functions                                     |
| --------------- | --------------- | ------------------- | ------------------------------------------------- |
| Main Trading    | _/15 _ \* \* \* | trading_analysis.py | `_process_symbol()`, `_execute_trade()`           |
| Exit Strategy   | _/5 _ \* \* \*  | trailing_5m.py      | `_process_trailing_stop()`, `_check_partial_tp()` |
| ML Scoring      | On-demand       | ml_scorer.py        | `score()`, `_load_all_models()`                   |
| Composite       | On-demand       | runtime.py          | `_compute_composite_signal()`                     |
| Signal Gate     | On-demand       | signal_gate.py      | `process_signal()`                                |
| Order Execution | On-demand       | runtime.py          | `_execute_trade()`, `_create_oco_bracket()`       |

---

## How to View

1. **mermaid.live**: Copy any code block and paste at https://mermaid.live
2. **VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **GitHub**: Push this file - diagrams render automatically
4. **Export to PNG/SVG**:
   ```bash
   npx @mermaid-js/mermaid-cli -i trading_pipeline_flowchart.md -o flowchart.png
   ```
