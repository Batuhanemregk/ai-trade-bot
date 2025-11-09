"""
Train 9 symmetric binary LightGBM models with 18-month data.
Target AUC: 0.70-0.80
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from ml.training.train_lgbm_per_symbol_tf import LGBMTrainerPerSymbolTF

def main():
    logger.info("="*80)
    logger.info("MULTICLASS MODEL TRAINING (LONG=2, SHORT=0, FLAT=1)")
    logger.info("Configuration:")
    logger.info("  - Data: 18 months")
    logger.info("  - Label: Multiclass (LONG=2, SHORT=0, FLAT=1)")
    logger.info("  - Threshold: 0.20%")
    logger.info("  - Forward bars: 3")
    logger.info("  - Include FLAT: Yes (with reduced weight)")
    logger.info("  - Target AUC: 0.70-0.80")
    logger.info("="*80)
    
    trainer = LGBMTrainerPerSymbolTF()
    results = trainer.train_all_models()
    
    # Generate report
    report = trainer.generate_report()
    print("\n" + report)
    
    # Save report
    report_path = Path("docs/MULTICLASS_TRAINING_REPORT.md")
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"✅ Training complete! Report saved: {report_path}")
    
    # Check if AUC targets met
    auc_values = [r.get('auc', 0) for r in results.values() if 'auc' in r]
    avg_auc = sum(auc_values) / len(auc_values) if auc_values else 0
    
    logger.info(f"\nAverage AUC: {avg_auc:.3f}")
    if avg_auc >= 0.70:
        logger.success(f"🎯 Target AUC achieved! ({avg_auc:.3f} >= 0.70)")
    else:
        logger.warning(f"⚠️ AUC below target: {avg_auc:.3f} < 0.70")

if __name__ == '__main__':
    main()
