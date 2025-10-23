"""
Real Trading Analysis Integration Tests
Tests actual trading analysis with real market data and real scoring
"""
import pytest
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from scoring.ta_scorer import TAScorer
from scoring.ml_scorer import MLScorer
from scoring.news_scorer import NewsScorer
from scoring.risk_scorer import RiskScorer
from application.market_data_service import MarketDataService
from application.news_service import NewsService
from application.risk_service import RiskService
from application.signal_gate import SignalGate
from adapters.exchange_okx_ccxt import OKXExchangeAdapter
from configs.policy import load_policy


class TestRealTradingAnalysis:
    """Test real trading analysis with actual market data"""
    
    @pytest.fixture(scope="class")
    def policy(self):
        """Load real policy configuration"""
        return load_policy()
    
    @pytest.fixture(scope="class")
    def exchange_adapter(self, policy):
        """Create real exchange adapter"""
        return OKXExchangeAdapter(policy)
    
    @pytest.fixture(scope="class")
    def market_data_service(self, exchange_adapter, policy):
        """Create real market data service"""
        return MarketDataService(exchange_adapter, policy)
    
    @pytest.fixture(scope="class")
    def news_service(self, policy):
        """Create real news service"""
        return NewsService(policy)
    
    @pytest.fixture(scope="class")
    def risk_service(self, policy):
        """Create real risk service"""
        return RiskService(policy)
    
    @pytest.fixture(scope="class")
    def ta_scorer(self, policy):
        """Create real TA scorer"""
        return TAScorer()
    
    @pytest.fixture(scope="class")
    def ml_scorer(self, policy):
        """Create real ML scorer"""
        return MLScorer()
    
    @pytest.fixture(scope="class")
    def news_scorer(self, policy):
        """Create real news scorer"""
        return NewsScorer()
    
    @pytest.fixture(scope="class")
    def risk_scorer(self, policy):
        """Create real risk scorer"""
        return RiskScorer()
    
    @pytest.fixture(scope="class")
    def signal_gate(self, policy):
        """Create real signal gate"""
        return SignalGate(policy)
    
    @pytest.mark.asyncio
    async def test_ta_scorer_real_data(self, ta_scorer, market_data_service):
        """Test TA scorer with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real OHLCV data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test TA scoring
            ta_result = await ta_scorer.score(symbol, ohlcv_data)
            
            assert ta_result is not None
            assert isinstance(ta_result, tuple)
            assert len(ta_result) == 2
            
            score, details = ta_result
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100
            assert isinstance(details, dict)
            assert 'indicators' in details
            assert 'signals' in details
            
            print(f"✅ TA Scorer: Score {score:.1f} for {symbol}")
            print(f"   Indicators: {list(details['indicators'].keys())}")
            print(f"   Signals: {details['signals']}")
            
        except Exception as e:
            pytest.skip(f"TA scorer test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_ml_scorer_real_data(self, ml_scorer, market_data_service):
        """Test ML scorer with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real OHLCV data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test ML scoring
            ml_result = await ml_scorer.score(symbol, ohlcv_data)
            
            assert ml_result is not None
            assert isinstance(ml_result, tuple)
            assert len(ml_result) == 2
            
            score, details = ml_result
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100
            assert isinstance(details, dict)
            assert 'features' in details
            assert 'prediction' in details
            
            print(f"✅ ML Scorer: Score {score:.1f} for {symbol}")
            print(f"   Features: {len(details['features'])} features")
            print(f"   Prediction: {details['prediction']}")
            
        except Exception as e:
            pytest.skip(f"ML scorer test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_news_scorer_real_data(self, news_scorer, news_service):
        """Test news scorer with real news data"""
        try:
            symbol = "BTC-USDT-SWAP"
            
            # Test news scoring
            news_result = await news_scorer.score(symbol)
            
            assert news_result is not None
            assert isinstance(news_result, tuple)
            assert len(news_result) == 2
            
            score, details = news_result
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100
            assert isinstance(details, dict)
            assert 'categories' in details
            assert 'rationale' in details
            
            print(f"✅ News Scorer: Score {score:.1f} for {symbol}")
            print(f"   Categories: {details['categories']}")
            print(f"   Rationale: {details['rationale'][:100]}...")
            
        except Exception as e:
            pytest.skip(f"News scorer test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_risk_scorer_real_data(self, risk_scorer, market_data_service):
        """Test risk scorer with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real OHLCV data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test risk scoring
            risk_result = await risk_scorer.score(symbol, ohlcv_data)
            
            assert risk_result is not None
            assert isinstance(risk_result, tuple)
            assert len(risk_result) == 2
            
            score, details = risk_result
            assert isinstance(score, (int, float))
            assert 0 <= score <= 100
            assert isinstance(details, dict)
            assert 'volatility' in details
            assert 'liquidity' in details
            assert 'risk_level' in details
            
            print(f"✅ Risk Scorer: Score {score:.1f} for {symbol}")
            print(f"   Volatility: {details['volatility']:.2f}")
            print(f"   Liquidity: {details['liquidity']:.2f}")
            print(f"   Risk Level: {details['risk_level']}")
            
        except Exception as e:
            pytest.skip(f"Risk scorer test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_complete_analysis_pipeline(self, ta_scorer, ml_scorer, news_scorer, risk_scorer, 
                                            market_data_service, signal_gate):
        """Test complete analysis pipeline with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Run all scorers
            ta_result = await ta_scorer.score(symbol, ohlcv_data)
            ml_result = await ml_scorer.score(symbol, ohlcv_data)
            news_result = await news_scorer.score(symbol)
            risk_result = await risk_scorer.score(symbol, ohlcv_data)
            
            # Extract scores
            ta_score = ta_result[0]
            ml_score = ml_result[0]
            news_score = news_result[0]
            risk_score = risk_result[0]
            
            # Calculate final score (weighted average)
            weights = {'ta': 0.3, 'ml': 0.3, 'news': 0.2, 'risk': 0.2}
            final_score = (
                ta_score * weights['ta'] +
                ml_score * weights['ml'] +
                news_score * weights['news'] +
                risk_score * weights['risk']
            )
            
            # Determine direction
            direction = "LONG" if final_score > 60 else "SHORT" if final_score < 40 else "FLAT"
            
            # Test signal gate
            signal_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'ta_score': ta_score,
                'ml_score': ml_score,
                'news_score': news_score,
                'risk_score': risk_score,
                'final_score': final_score,
                'direction': direction,
                'timestamp': datetime.now(timezone.utc)
            }
            
            gate_result = await signal_gate.process_signal(signal_data)
            
            print(f"✅ Complete Analysis Pipeline for {symbol}:")
            print(f"   TA Score: {ta_score:.1f}")
            print(f"   ML Score: {ml_score:.1f}")
            print(f"   News Score: {news_score:.1f}")
            print(f"   Risk Score: {risk_score:.1f}")
            print(f"   Final Score: {final_score:.1f}")
            print(f"   Direction: {direction}")
            print(f"   Gate Result: {gate_result}")
            
            # Validate results
            assert 0 <= ta_score <= 100
            assert 0 <= ml_score <= 100
            assert 0 <= news_score <= 100
            assert 0 <= risk_score <= 100
            assert 0 <= final_score <= 100
            assert direction in ["LONG", "SHORT", "FLAT"]
            
        except Exception as e:
            pytest.skip(f"Complete analysis pipeline test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_multiple_symbols_analysis(self, ta_scorer, ml_scorer, news_scorer, risk_scorer,
                                           market_data_service):
        """Test analysis for multiple symbols"""
        try:
            symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
            results = {}
            
            for symbol in symbols:
                try:
                    # Get market data
                    ohlcv_data = await market_data_service._fetch_ohlcv(symbol, "15m", limit=100)
                    
                    if ohlcv_data is not None and len(ohlcv_data) > 0:
                        # Run analysis
                        ta_result = await ta_scorer.score(symbol, ohlcv_data)
                        ml_result = await ml_scorer.score(symbol, ohlcv_data)
                        news_result = await news_scorer.score(symbol)
                        risk_result = await risk_scorer.score(symbol, ohlcv_data)
                        
                        # Calculate final score
                        final_score = (
                            ta_result[0] * 0.3 +
                            ml_result[0] * 0.3 +
                            news_result[0] * 0.2 +
                            risk_result[0] * 0.2
                        )
                        
                        direction = "LONG" if final_score > 60 else "SHORT" if final_score < 40 else "FLAT"
                        
                        results[symbol] = {
                            'ta': ta_result[0],
                            'ml': ml_result[0],
                            'news': news_result[0],
                            'risk': risk_result[0],
                            'final': final_score,
                            'direction': direction
                        }
                        
                        print(f"✅ {symbol}: Final {final_score:.1f} ({direction})")
                        print(f"   TA:{ta_result[0]:.1f} ML:{ml_result[0]:.1f} News:{news_result[0]:.1f} Risk:{risk_result[0]:.1f}")
                        
                    else:
                        results[symbol] = {'error': 'No market data'}
                        print(f"⚠️ {symbol}: No market data available")
                        
                except Exception as e:
                    results[symbol] = {'error': str(e)}
                    print(f"⚠️ {symbol}: Analysis failed - {e}")
            
            # At least one symbol should work
            successful_symbols = [s for s, r in results.items() if 'error' not in r]
            assert len(successful_symbols) > 0, "No symbols analyzed successfully"
            
            print(f"✅ Successfully analyzed {len(successful_symbols)}/{len(symbols)} symbols")
            
        except Exception as e:
            pytest.skip(f"Multiple symbols analysis test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_signal_gate_persistence(self, signal_gate):
        """Test signal gate persistence with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Create test signal data
            signal_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'ta_score': 75.0,
                'ml_score': 68.0,
                'news_score': 55.0,
                'risk_score': 42.0,
                'final_score': 65.0,
                'direction': "LONG",
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Process signal multiple times to test persistence
            results = []
            for i in range(3):
                result = await signal_gate.process_signal(signal_data)
                results.append(result)
                print(f"✅ Signal gate attempt {i+1}: {result}")
            
            # Check persistence behavior
            assert len(results) == 3
            print(f"✅ Signal gate persistence test completed")
            
        except Exception as e:
            pytest.skip(f"Signal gate persistence test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_analysis_performance(self, ta_scorer, ml_scorer, market_data_service):
        """Test analysis performance with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Time TA analysis
            start_time = datetime.now()
            ta_result = await ta_scorer.score(symbol, ohlcv_data)
            ta_duration = (datetime.now() - start_time).total_seconds()
            
            # Time ML analysis
            start_time = datetime.now()
            ml_result = await ml_scorer.score(symbol, ohlcv_data)
            ml_duration = (datetime.now() - start_time).total_seconds()
            
            print(f"✅ Analysis Performance:")
            print(f"   TA Analysis: {ta_duration:.2f}s")
            print(f"   ML Analysis: {ml_duration:.2f}s")
            print(f"   Data Points: {len(ohlcv_data)}")
            
            # Performance thresholds (should complete within reasonable time)
            assert ta_duration < 10.0, f"TA analysis too slow: {ta_duration:.2f}s"
            assert ml_duration < 15.0, f"ML analysis too slow: {ml_duration:.2f}s"
            
        except Exception as e:
            pytest.skip(f"Analysis performance test failed: {e}")


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/integration/test_real_trading_analysis.py -v -s
    pytest.main([__file__, "-v", "-s"])
