# LGBM Training Report

**Date**: 2025-11-01 00:38:15
**Models Trained**: 9

## Model Performance

| Symbol_TF | AUC    | Accuracy | Precision | Recall | F1     | Balanced Acc |
|-----------|--------|----------|-----------|--------|--------|--------------|
| BTCUSDT_15m | 0.6659 | 0.8256 | 0.2872 | 0.1666 | 0.2038 | 0.5494 |
| BTCUSDT_1h | 0.5789 | 0.6604 | 0.3510 | 0.2893 | 0.3058 | 0.5425 |
| BTCUSDT_4h | 0.5554 | 0.5307 | 0.3986 | 0.4690 | 0.4235 | 0.5199 |
| ETHUSDT_15m | 0.6067 | 0.6748 | 0.3888 | 0.2926 | 0.3245 | 0.5557 |
| ETHUSDT_1h | 0.5645 | 0.5647 | 0.4236 | 0.4302 | 0.4224 | 0.5385 |
| ETHUSDT_4h | 0.5444 | 0.5363 | 0.4746 | 0.4882 | 0.4641 | 0.5344 |
| SOLUSDT_15m | 0.5828 | 0.6220 | 0.4045 | 0.3520 | 0.3670 | 0.5502 |
| SOLUSDT_1h | 0.5664 | 0.5622 | 0.4787 | 0.4555 | 0.4476 | 0.5480 |
| SOLUSDT_4h | 0.5292 | 0.5196 | 0.4766 | 0.4791 | 0.4482 | 0.5214 |

## Summary

- **Training Method**: Time-series cross-validation (5 folds)
- **Label**: Binary (price up >0.25% in 3 bars)
- **Features**: 60-73 (depending on MTF availability)
- **Hyperparameters**: Standard LightGBM config with regularization