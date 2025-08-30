# scripts/run_scoring_demo.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time

import numpy as np
import pandas as pd

from config import TRADING_CFG
from llm.sentiment_client import score_news
from scoring.fusion import fuse_and_decide
from ta.engine import compute_ta_score


def fake_ohlcv(n=300, start=100.0):
    """Test için sahte OHLCV verisi oluştur"""
    np.random.seed(42)
    rets = np.random.normal(0, 0.003, size=n)
    price = start * np.exp(np.cumsum(rets))
    close = pd.Series(price)
    high = close * (1 + np.random.uniform(0, 0.005, size=n))
    low  = close * (1 - np.random.uniform(0, 0.005, size=n))
    open_ = close.shift(1).fillna(close.iloc[0])
    vol = pd.Series(np.random.lognormal(mean=10, sigma=0.5, size=n))
    df = pd.DataFrame({"open":open_,"high":high,"low":low,"close":close,"volume":vol})
    return df

if __name__ == "__main__":
    print("🚀 Starting Scoring Demo...")
    print(f"Config: TA weight={TRADING_CFG['W_TA']}, News weight={TRADING_CFG['W_NEWS']}")
    print(f"Thresholds: TA_LONG={TRADING_CFG['TA_LONG_TH']}, TA_SHORT={TRADING_CFG['TA_SHORT_TH']}")
    print(f"Final thresholds: LONG={TRADING_CFG['FINAL_LONG_TH']}, SHORT={TRADING_CFG['FINAL_SHORT_TH']}")
    print()

    # Test verisi oluştur
    ohlcv = fake_ohlcv()
    headlines = [
        "Major crypto exchange hacked; $100M stolen",
        "Regulatory crackdown intensifies; trading volumes plummet",
        "Technical glitch causes widespread liquidations"
    ]

    print("📊 Test Data:")
    print(f"   OHLCV: {len(ohlcv)} bars, last close: {ohlcv['close'].iloc[-1]:.2f}")
    print(f"   Headlines: {len(headlines)} items")
    print()

    # 1) TA skoru hesapla
    print("🔍 Computing TA Score...")
    start_time = time.time()
    ta_out = compute_ta_score(ohlcv, TRADING_CFG)
    ta_time = time.time() - start_time

    print(f"   TA Score: {ta_out['ta_score']:.3f}")
    print("   Sub-scores:")
    for key, value in ta_out['subs'].items():
        print(f"     {key}: {value:.3f}")
    print(f"   Computation time: {ta_time:.3f}s")
    print()

    # 2) LLM haber skoru
    print("🤖 Computing News Score...")
    start_time = time.time()
    news_out = score_news(headlines)
    news_time = time.time() - start_time

    print(f"   News Score: {news_out['news_score']:.3f}")
    print(f"   Usage: {news_out.get('usage', 'No usage data')}")
    print(f"   Computation time: {news_time:.3f}s")
    print()

    # 3) Füzyon ve karar
    print("⚡ Computing Fusion & Decision...")
    final_score, decision = fuse_and_decide(ta_out["ta_score"], news_out["news_score"], TRADING_CFG)

    print(f"   Final Score: {final_score:.3f}")
    print(f"   Decision: {decision}")
    print()

    # 4) Detaylı analiz
    print("📋 Detailed Analysis:")
    w_ta = TRADING_CFG['W_TA']
    w_news = TRADING_CFG['W_NEWS']
    weighted_ta = w_ta * ta_out['ta_score']
    weighted_news = w_news * news_out['news_score']

    print(f"   Weighted TA: {w_ta} × {ta_out['ta_score']:.3f} = {weighted_ta:.3f}")
    print(f"   Weighted News: {w_news} × {news_out['news_score']:.3f} = {weighted_news:.3f}")
    print(f"   Sum: {weighted_ta:.3f} + {weighted_news:.3f} = {final_score:.3f}")
    print()

    # 5) Karar mantığı
    print("🎯 Decision Logic:")
    ta_long_ok = ta_out['ta_score'] >= TRADING_CFG['TA_LONG_TH']
    ta_short_ok = ta_out['ta_score'] <= TRADING_CFG['TA_SHORT_TH']
    final_long_ok = final_score >= TRADING_CFG['FINAL_LONG_TH']
    final_short_ok = final_score <= TRADING_CFG['FINAL_SHORT_TH']

    print(f"   TA Long threshold ({TRADING_CFG['TA_LONG_TH']}): {ta_out['ta_score']:.3f} >= {TRADING_CFG['TA_LONG_TH']} → {ta_long_ok}")
    print(f"   TA Short threshold ({TRADING_CFG['TA_SHORT_TH']}): {ta_out['ta_score']:.3f} <= {TRADING_CFG['TA_SHORT_TH']} → {ta_short_ok}")
    print(f"   Final Long threshold ({TRADING_CFG['FINAL_LONG_TH']}): {final_score:.3f} >= {TRADING_CFG['FINAL_LONG_TH']} → {final_long_ok}")
    print(f"   Final Short threshold ({TRADING_CFG['FINAL_SHORT_TH']}): {final_score:.3f} <= {TRADING_CFG['FINAL_SHORT_TH']} → {final_short_ok}")
    print()

    if decision == "LONG":
        print("✅ LONG signal generated!")
        print(f"   Conditions: TA Long OK ({ta_long_ok}) AND Final Long OK ({final_long_ok})")
    elif decision == "SHORT":
        print("✅ SHORT signal generated!")
        print(f"   Conditions: TA Short OK ({ta_short_ok}) AND Final Short OK ({final_short_ok})")
    else:
        print("⏸ FLAT - No signal")
        print(f"   TA Long: {ta_long_ok}, TA Short: {ta_short_ok}")
        print(f"   Final Long: {final_long_ok}, Final Short: {final_short_ok}")

    print("\n🎉 Demo completed successfully!")
