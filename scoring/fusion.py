# scoring/fusion.py

def fuse_and_decide(ta_score: float, news_score: float, cfg: dict):
    """
    TA ve news skorlarını ağırlıklarla birleştir, eşiklere göre karar ver
    
    Args:
        ta_score: TA skoru (-1.0 .. +1.0)
        news_score: News skoru (-1.0 .. +1.0)
        cfg: Konfigürasyon dict'i
        
    Returns:
        Tuple[float, str]: (final_score, decision)
        
    Decision Rules:
        - LONG: final_score >= FINAL_LONG_TH AND ta_score >= TA_LONG_TH
        - SHORT: final_score <= FINAL_SHORT_TH AND ta_score <= TA_SHORT_TH
        - FLAT: otherwise
        
    IMPORTANT: LONG and SHORT are mutually exclusive - only one can be true at a time.
    """
    w_ta = cfg["W_TA"]
    w_news = cfg["W_NEWS"]

    # Ağırlıklı ortalama
    final_score = w_ta * ta_score + w_news * news_score

    # Karar verme - MUTUALLY EXCLUSIVE
    decision = "FLAT"

    # Debug log ekle
    print(f"🔍 DEBUG FUSION: ta_score={ta_score:.3f}, news_score={news_score:.3f}, final_score={final_score:.3f}")
    print(f"🔍 DEBUG THRESHOLDS: TA_LONG_TH={cfg['TA_LONG_TH']}, FINAL_LONG_TH={cfg['FINAL_LONG_TH']}")
    print(f"🔍 DEBUG THRESHOLDS: TA_SHORT_TH={cfg['TA_SHORT_TH']}, FINAL_SHORT_TH={cfg['FINAL_SHORT_TH']}")

    # LONG ve SHORT şartlarını kontrol et - MUTUALLY EXCLUSIVE
    long_condition = final_score >= cfg["FINAL_LONG_TH"] and ta_score >= cfg["TA_LONG_TH"]
    short_condition = final_score <= cfg["FINAL_SHORT_TH"] and ta_score <= cfg["TA_SHORT_TH"]

    # CRITICAL FIX: Ensure mutual exclusivity
    if long_condition and short_condition:
        # This should NEVER happen with proper threshold configuration
        # If both conditions are met, choose the stronger signal based on absolute distance from thresholds
        long_strength = abs(final_score - cfg["FINAL_LONG_TH"])
        short_strength = abs(final_score - cfg["FINAL_SHORT_TH"])

        if long_strength > short_strength:
            decision = "LONG"
            print(f"⚖️ DECISION: LONG (conflict resolved) - |final-long_th|={long_strength:.3f} > |final-short_th|={short_strength:.3f}")
        else:
            decision = "SHORT"
            print(f"⚖️ DECISION: SHORT (conflict resolved) - |final-short_th|={short_strength:.3f} >= |final-long_th|={long_strength:.3f}")
    elif long_condition:
        decision = "LONG"
        print(f"✅ DECISION: LONG - final_score {final_score:.3f} >= {cfg['FINAL_LONG_TH']} AND ta_score {ta_score:.3f} >= {cfg['TA_LONG_TH']}")
    elif short_condition:
        decision = "SHORT"
        print(f"✅ DECISION: SHORT - final_score {final_score:.3f} <= {cfg['FINAL_SHORT_TH']} AND ta_score {ta_score:.3f} <= {cfg['TA_SHORT_TH']}")
    else:
        print("⏸ DECISION: FLAT - No threshold met")

    return final_score, decision
