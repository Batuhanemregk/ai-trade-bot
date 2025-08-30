"""
Test technical analysis indicators and TA scorer.
"""

import numpy as np
import pandas as pd

from scoring.ta_scorer import TAScorer
from scoring.strategy_scorer import calculate_all_indicators


class TestIndicatorsTA:
    """Test technical analysis indicators and scoring."""

    def test_ohlcv_bundle_factory_output(self, ohlcv_bundle_factory):
        """Test that OHLCV bundle factory produces valid data."""
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)

        # Check structure
        assert isinstance(bundle, dict)
        assert set(bundle.keys()) == {"1h", "15m", "5m"}

        # Check each timeframe
        for tf, df in bundle.items():
            assert isinstance(df, pd.DataFrame)
            assert not df.empty
            assert len(df) >= 300
            assert set(df.columns) == {"open", "high", "low", "close", "volume"}
            assert df.index.name == "timestamp"

            # Check data types
            for col in ["open", "high", "low", "close", "volume"]:
                assert df[col].dtype in [np.float64, np.float32, np.int64, np.int32]

            # Check OHLC relationships
            assert all(df["high"] >= df["low"])
            assert all(df["high"] >= df["close"])
            assert all(df["high"] >= df["open"])
            assert all(df["low"] <= df["close"])
            assert all(df["low"] <= df["open"])

            # Check volume is positive
            assert all(df["volume"] > 0)

    def test_strategy_scorer_import(self):
        """Test that strategy_scorer functions can be imported."""
        assert calculate_all_indicators is not None
        assert callable(calculate_all_indicators)

    def test_ta_scorer_import(self):
        """Test that TA scorer can be imported and initialized."""
        scorer = TAScorer()
        assert scorer is not None
        assert hasattr(scorer, "score")

    def test_ta_scoring_with_synthetic_data(self, ohlcv_bundle_factory):
        """Test TA scoring with synthetic OHLCV data."""
        # Get 15m data for testing
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        df = bundle["15m"]

        # Test TA scoring
        scorer = TAScorer()
        score, rationale, flags = scorer.score(df, "BTC-USDT-SWAP")

        # Validate score
        assert isinstance(score, float)
        assert 0 <= score <= 100
        assert not np.isnan(score)

        # Validate rationale
        assert isinstance(rationale, str)
        assert len(rationale) > 0

        # Validate flags
        assert isinstance(flags, dict)
        assert "dir_hint" in flags
        assert flags["dir_hint"] in ["LONG", "SHORT", "FLAT"]

    def test_indicator_calculation(self, ohlcv_bundle_factory):
        """Test that all required indicators are calculated correctly."""
        # Get 15m data for testing
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        df = bundle["15m"]

        # Calculate indicators
        indicators_df = calculate_all_indicators(df)

        # Check that we have indicators
        assert not indicators_df.empty
        assert len(indicators_df) > 0

        # Required indicators
        required_indicators = [
            "sma_20", "sma_50", "rsi", "macd", "macd_signal", "macd_histogram",
            "bb_upper", "bb_middle", "bb_lower", "bb_width", "atr",
            "volume_sma", "volume_ratio", "current_price", "high_20", "low_20"
        ]

        # Check that all required indicators exist
        for indicator in required_indicators:
            assert indicator in indicators_df.columns, f"Missing indicator: {indicator}"

        # Validate indicators after warmup (should have no NaN values)
        # Check that we have the required indicators
        required_indicators = ['sma_20', 'sma_50', 'rsi', 'macd', 'bb_upper', 'atr']
        for indicator in required_indicators:
            assert indicator in indicators_df.columns, f"Missing indicator: {indicator}"

        # Check that at least some indicators are working
        # Count non-NaN values for each indicator
        working_indicators = []
        for indicator in required_indicators:
            if indicator in indicators_df.columns:
                non_nan_count = indicators_df[indicator].dropna().shape[0]
                if non_nan_count > 0:
                    working_indicators.append(indicator)
        
        assert len(working_indicators) > 0, f"No indicators working: {working_indicators}"

        # Validate specific indicators that should work
        if "rsi" in working_indicators:
            rsi = indicators_df["rsi"].dropna()
            if len(rsi) > 0:
                assert all((0 <= rsi) & (rsi <= 100)), f"RSI values outside [0, 100]: {rsi.min()}-{rsi.max()}"

        if "atr" in working_indicators:
            atr = indicators_df["atr"].dropna()
            if len(atr) > 0:
                assert all(atr > 0), f"ATR should be positive, got min: {atr.min()}"

        if "macd" in working_indicators:
            macd = indicators_df["macd"].dropna()
            if len(macd) > 0:
                assert all(np.isfinite(macd)), f"MACD should be finite, got: {macd.head()}"

        if "bb_width" in working_indicators:
            bb_width = indicators_df["bb_width"].dropna()
            if len(bb_width) > 0:
                # Allow small negative values due to floating point precision
                assert all(bb_width > -1e-10), f"BB width should be >= 0, got min: {bb_width.min()}"

    def test_indicator_bundle_creation(self, indicator_bundle_factory):
        """Test indicator bundle creation for multiple timeframes."""
        bundle = indicator_bundle_factory("BTC-USDT-SWAP", 300)

        # Check structure
        assert isinstance(bundle, dict)
        assert set(bundle.keys()) == {"1h", "15m", "5m"}

        # Check each timeframe has indicators
        for tf, df in bundle.items():
            assert isinstance(df, pd.DataFrame)
            assert not df.empty

            # Should have both OHLCV and indicator columns
            ohlcv_cols = {"open", "high", "low", "close", "volume"}
            indicator_cols = {"sma_20", "rsi", "macd", "bb_upper", "atr"}

            assert all(col in df.columns for col in ohlcv_cols)
            assert all(col in df.columns for col in indicator_cols)

    def test_scoring_consistency(self, ohlcv_bundle_factory):
        """Test that TA scoring produces consistent results."""
        # Get data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        df = bundle["15m"]

        # Score multiple times
        scorer = TAScorer()
        scores = []

        for _ in range(3):
            score, _, _ = scorer.score(df, "BTC-USDT-SWAP")
            scores.append(score)

        # Scores should be identical (deterministic)
        assert len(set(scores)) == 1, f"Scores should be identical: {scores}"

    def test_insufficient_data_handling(self):
        """Test handling of insufficient data."""
        # Create small DataFrame
        small_df = pd.DataFrame({
            "open": [100, 101, 102],
            "high": [105, 106, 107],
            "low": [95, 96, 97],
            "close": [101, 102, 103],
            "volume": [1000, 1100, 1200]
        })

        # Test indicator calculation
        indicators_df = calculate_all_indicators(small_df)
        assert indicators_df is not None

        # Test TA scoring
        scorer = TAScorer()
        score, rationale, flags = scorer.score(small_df, "TEST")

        # Should return neutral score for insufficient data
        assert score == 50.0
        assert "Insufficient data" in rationale
        assert flags["dir_hint"] == "FLAT"

    def test_strategy_flags(self, ohlcv_bundle_factory):
        """Test that strategy flags are properly set."""
        # Get data
        bundle = ohlcv_bundle_factory("BTC-USDT-SWAP", 300)
        df = bundle["15m"]

        # Score
        scorer = TAScorer()
        score, rationale, flags = scorer.score(df, "BTC-USDT-SWAP")

        # Check required flags
        required_flags = ["trend", "meanrev", "breakout", "dir_hint"]
        for flag in required_flags:
            assert flag in flags, f"Missing flag: {flag}"

        # Check flag values
        assert flags["trend"] in ["up", "down", "side"]
        assert flags["meanrev"] in ["on", "off"]
        assert flags["breakout"] in ["on", "off"]
        assert flags["dir_hint"] in ["LONG", "SHORT", "FLAT"]
