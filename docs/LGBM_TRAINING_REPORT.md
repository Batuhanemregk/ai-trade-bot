# LGBM Training Report

**Date**: 2025-10-31 23:49:02
**Models Trained**: 9

## Model Performance

| Symbol_TF | AUC    | Accuracy | Precision | Recall | F1     | Balanced Acc |
|-----------|--------|----------|-----------|--------|--------|--------------|
| BTCUSDT_15m | 0.6577 | 0.8458 | 0.3039 | 0.0948 | 0.1413 | 0.5322 |
| BTCUSDT_1h | 0.5873 | 0.6595 | 0.4183 | 0.2759 | 0.3065 | 0.5460 |
| BTCUSDT_4h | 0.5304 | 0.5173 | 0.4235 | 0.5085 | 0.4261 | 0.5166 |
| ETHUSDT_15m | 0.5988 | 0.7097 | 0.4253 | 0.1508 | 0.2129 | 0.5352 |
| ETHUSDT_1h | 0.5689 | 0.5766 | 0.4414 | 0.3693 | 0.3901 | 0.5411 |
| ETHUSDT_4h | 0.5596 | 0.5318 | 0.5410 | 0.3980 | 0.4246 | 0.5378 |
| SOLUSDT_15m | 0.6000 | 0.6579 | 0.4602 | 0.2124 | 0.2576 | 0.5390 |
| SOLUSDT_1h | 0.5678 | 0.5661 | 0.5013 | 0.3683 | 0.3881 | 0.5408 |
| SOLUSDT_4h | 0.5442 | 0.5128 | 0.5803 | 0.4826 | 0.4493 | 0.5306 |

## Summary

- **Training Method**: Time-series cross-validation (5 folds)
- **Label**: Binary (price up >0.25% in 3 bars)
- **Features**: 60-73 (depending on MTF availability)
- **Hyperparameters**: Standard LightGBM config with regularization