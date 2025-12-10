# LGBM Training Report

**Date**: 2025-12-08 17:04:27
**Models Trained**: 9

## Model Performance

| Symbol_TF | AUC    | Accuracy | Precision | Recall | F1     | Balanced Acc |
|-----------|--------|----------|-----------|--------|--------|--------------|
| BTCUSDT_15m | 0.6513 | 0.8001 | 0.3238 | 0.1985 | 0.2338 | 0.5540 |
| BTCUSDT_1h | 0.5823 | 0.6451 | 0.3823 | 0.3579 | 0.3584 | 0.5546 |
| BTCUSDT_4h | 0.5475 | 0.5609 | 0.4286 | 0.4668 | 0.4417 | 0.5404 |
| ETHUSDT_15m | 0.6097 | 0.6745 | 0.3966 | 0.3188 | 0.3477 | 0.5645 |
| ETHUSDT_1h | 0.5694 | 0.5858 | 0.4568 | 0.4065 | 0.4262 | 0.5524 |
| ETHUSDT_4h | 0.5586 | 0.5464 | 0.5061 | 0.5292 | 0.5158 | 0.5452 |
| SOLUSDT_15m | 0.5894 | 0.6289 | 0.4118 | 0.3284 | 0.3440 | 0.5504 |
| SOLUSDT_1h | 0.5742 | 0.5772 | 0.5012 | 0.3337 | 0.3778 | 0.5426 |
| SOLUSDT_4h | 0.5359 | 0.5151 | 0.4547 | 0.4629 | 0.4444 | 0.5105 |

## Summary

- **Training Method**: Time-series cross-validation (5 folds)
- **Label**: Binary (price up >0.25% in 3 bars)
- **Features**: 60-73 (depending on MTF availability)
- **Hyperparameters**: Standard LightGBM config with regularization