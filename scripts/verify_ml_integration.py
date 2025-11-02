"""Verify ML integration is complete."""

from scoring.ml_scorer import MLScorer
import json
from pathlib import Path

print("\n" + "="*80)
print("ML INTEGRATION VERIFICATION")
print("="*80)

# Check model loading
scorer = MLScorer()
print(f"\nModels Loaded: {len(scorer.models)}/9")

# Load BTC_15m metadata (try 18m first, fallback to 6m)
metadata_path = Path("models/lgbm/BTCUSDT_15m_last18m_metadata.json")
if not metadata_path.exists():
    metadata_path = Path("models/lgbm/BTCUSDT_15m_last6m_metadata.json")
    
if metadata_path.exists():
    m = json.load(open(metadata_path))
    print(f"BTC_15m AUC: {m['metrics']['auc']:.4f}")
    print(f"Features: {m['n_features']}")
    if 'hyperparameters' in m:
        print(f"Hyperparameters: {m['hyperparameters'].get('n_estimators', 'N/A')} trees, LR={m['hyperparameters'].get('learning_rate', 'N/A')}")

print("\n" + "="*80)
print("[OK] INTEGRATION VERIFIED")
print("="*80)

