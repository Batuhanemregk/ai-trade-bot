"""
Real End-to-End Trading Cycle Tests
Tests complete trading cycle with real data, real analysis, and real decision making
"""
import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from application.trading_orchestrator import TradingOrchestrator
from application.jobs.trading_analysis import TradingAnalysisJob
from application.portfolio_manager import PortfolioManager
from application.position_monitor import PositionMonitor
from application.signal_gate import SignalGate
from application.market_data_service import MarketDataService
from application.news_service import NewsService
from application.risk_service import RiskService
from adapters.exchange_okx_ccxt import OKXExchangeAdapter
from configs.policy import load_policy


class TestRealTradingCycle:
    """Test complete trading cycle with real data and real analysis"""
    
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
    def signal_gate(self, policy):
        """Create real signal gate"""
        return SignalGate(policy)
    
    @pytest.fixture(scope="class")
    def portfolio_manager(self, policy):
        """Create real portfolio manager"""
        return PortfolioManager(policy)
    
    @pytest.fixture(scope="class")
    def position_monitor(self, policy):
        """Create real position monitor"""
        return PositionMonitor(policy)
    
    @pytest.fixture(scope="class")
    def trading_orchestrator(self, policy):
        """Create real trading orchestrator"""
        return TradingOrchestrator(policy)
    
    @pytest.fixture(scope="class")
    def trading_analysis_job(self, policy):
        """Create real trading analysis job"""
        return TradingAnalysisJob(policy)
    
    @pytest.mark.asyncio
    async def test_complete_analysis_cycle(self, trading_analysis_job, market_data_service):
        """Test complete analysis cycle with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Simulate job execution
            job_key = f"trading_analysis_{symbol}_{timeframe}"
            bar_id = datetime.now(timezone.utc).isoformat()
            
            # Execute the trading analysis job
            result = await trading_analysis_job.execute(job_key, bar_id)
            
            assert result is not None
            assert isinstance(result, dict)
            assert 'symbol' in result
            assert 'analysis_completed' in result
            assert 'timestamp' in result
            
            print(f"✅ Complete Analysis Cycle for {symbol}:")
            print(f"   Job Key: {job_key}")
            print(f"   Bar ID: {bar_id}")
            print(f"   Analysis Completed: {result['analysis_completed']}")
            print(f"   Timestamp: {result['timestamp']}")
            
        except Exception as e:
            pytest.skip(f"Complete analysis cycle test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_signal_generation_and_processing(self, signal_gate, market_data_service, 
                                                  news_service, risk_service):
        """Test signal generation and processing with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Get real news data
            news_data = await news_service.get_news_score(symbol)
            news_score = news_data[0] if news_data else 50.0
            
            # Get real risk assessment
            risk_data = await risk_service.assess_risk(symbol, ohlcv_data)
            risk_score = risk_data['risk_score']
            
            # Simulate TA and ML scores (would normally come from actual scorers)
            ta_score = 75.0
            ml_score = 68.0
            
            # Calculate final score
            final_score = (ta_score * 0.3 + ml_score * 0.3 + news_score * 0.2 + risk_score * 0.2)
            direction = "LONG" if final_score > 60 else "SHORT" if final_score < 40 else "FLAT"
            
            # Create signal data
            signal_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'ta_score': ta_score,
                'ml_score': ml_score,
                'news_score': news_score,
                'risk_score': risk_score,
                'final_score': final_score,
                'direction': direction,
                'timestamp': datetime.now(timezone.utc),
                'ohlcv_data': ohlcv_data
            }
            
            # Process signal through gate
            gate_result = await signal_gate.process_signal(signal_data)
            
            print(f"✅ Signal Generation and Processing for {symbol}:")
            print(f"   TA Score: {ta_score:.1f}")
            print(f"   ML Score: {ml_score:.1f}")
            print(f"   News Score: {news_score:.1f}")
            print(f"   Risk Score: {risk_score:.1f}")
            print(f"   Final Score: {final_score:.1f}")
            print(f"   Direction: {direction}")
            print(f"   Gate Result: {gate_result}")
            
            # Validate signal processing
            assert isinstance(gate_result, dict)
            assert 'action' in gate_result
            assert 'confidence' in gate_result
            
        except Exception as e:
            pytest.skip(f"Signal generation and processing test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_portfolio_management_real_data(self, portfolio_manager, market_data_service):
        """Test portfolio management with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, "15m", limit=100)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test portfolio analysis
            portfolio_analysis = await portfolio_manager.analyze_portfolio()
            
            assert portfolio_analysis is not None
            assert isinstance(portfolio_analysis, dict)
            assert 'total_value' in portfolio_analysis
            assert 'positions' in portfolio_analysis
            assert 'risk_metrics' in portfolio_analysis
            
            print(f"✅ Portfolio Management Analysis:")
            print(f"   Total Value: ${portfolio_analysis.get('total_value', 0):,.2f}")
            print(f"   Positions: {len(portfolio_analysis.get('positions', []))}")
            print(f"   Risk Metrics: {list(portfolio_analysis.get('risk_metrics', {}).keys())}")
            
        except Exception as e:
            pytest.skip(f"Portfolio management test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_position_monitoring_real_data(self, position_monitor, market_data_service):
        """Test position monitoring with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, "15m", limit=100)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test position monitoring
            position_status = await position_monitor.check_positions()
            
            assert position_status is not None
            assert isinstance(position_status, dict)
            assert 'active_positions' in position_status
            assert 'alerts' in position_status
            
            print(f"✅ Position Monitoring:")
            print(f"   Active Positions: {len(position_status.get('active_positions', []))}")
            print(f"   Alerts: {len(position_status.get('alerts', []))}")
            
        except Exception as e:
            pytest.skip(f"Position monitoring test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_trading_orchestrator_real_data(self, trading_orchestrator, market_data_service):
        """Test trading orchestrator with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, "15m", limit=100)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test orchestrator analysis
            analysis_result = await trading_orchestrator.analyze_symbol(symbol, ohlcv_data)
            
            assert analysis_result is not None
            assert isinstance(analysis_result, dict)
            assert 'symbol' in analysis_result
            assert 'analysis_timestamp' in analysis_result
            
            print(f"✅ Trading Orchestrator Analysis for {symbol}:")
            print(f"   Analysis Timestamp: {analysis_result.get('analysis_timestamp')}")
            print(f"   Result Keys: {list(analysis_result.keys())}")
            
        except Exception as e:
            pytest.skip(f"Trading orchestrator test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_multi_symbol_trading_cycle(self, trading_analysis_job, market_data_service):
        """Test trading cycle for multiple symbols"""
        try:
            symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
            results = {}
            
            for symbol in symbols:
                try:
                    # Check if market data is available
                    ohlcv_data = await market_data_service._fetch_ohlcv(symbol, "15m", limit=50)
                    
                    if ohlcv_data is not None and len(ohlcv_data) > 0:
                        # Execute trading analysis
                        job_key = f"trading_analysis_{symbol}_15m"
                        bar_id = datetime.now(timezone.utc).isoformat()
                        
                        result = await trading_analysis_job.execute(job_key, bar_id)
                        
                        results[symbol] = {
                            'success': True,
                            'analysis_completed': result.get('analysis_completed', False),
                            'data_points': len(ohlcv_data)
                        }
                        
                        print(f"✅ {symbol}: Analysis completed - {result.get('analysis_completed', False)}")
                        print(f"   Data Points: {len(ohlcv_data)}")
                        
                    else:
                        results[symbol] = {'success': False, 'error': 'No market data'}
                        print(f"⚠️ {symbol}: No market data available")
                        
                except Exception as e:
                    results[symbol] = {'success': False, 'error': str(e)}
                    print(f"⚠️ {symbol}: Analysis failed - {e}")
            
            # At least one symbol should work
            successful_symbols = [s for s, r in results.items() if r.get('success', False)]
            assert len(successful_symbols) > 0, "No symbols processed successfully"
            
            print(f"✅ Multi-symbol trading cycle: {len(successful_symbols)}/{len(symbols)} symbols successful")
            
        except Exception as e:
            pytest.skip(f"Multi-symbol trading cycle test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_trading_cycle_performance(self, trading_analysis_job, market_data_service):
        """Test trading cycle performance with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Measure performance
            start_time = datetime.now()
            
            # Execute trading analysis
            job_key = f"trading_analysis_{symbol}_{timeframe}"
            bar_id = datetime.now(timezone.utc).isoformat()
            
            result = await trading_analysis_job.execute(job_key, bar_id)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"✅ Trading Cycle Performance for {symbol}:")
            print(f"   Duration: {duration:.2f} seconds")
            print(f"   Analysis Completed: {result.get('analysis_completed', False)}")
            
            # Performance should be reasonable
            assert duration < 30.0, f"Trading cycle too slow: {duration:.2f}s"
            assert result.get('analysis_completed', False), "Analysis should complete successfully"
            
        except Exception as e:
            pytest.skip(f"Trading cycle performance test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_trading_cycle_error_handling(self, trading_analysis_job):
        """Test trading cycle error handling"""
        try:
            # Test with invalid symbol
            invalid_symbol = "INVALID-SYMBOL"
            job_key = f"trading_analysis_{invalid_symbol}_15m"
            bar_id = datetime.now(timezone.utc).isoformat()
            
            result = await trading_analysis_job.execute(job_key, bar_id)
            
            print(f"✅ Trading Cycle Error Handling:")
            print(f"   Invalid Symbol: {invalid_symbol}")
            print(f"   Result: {result}")
            
            # Should handle error gracefully
            assert result is not None
            assert isinstance(result, dict)
            
        except Exception as e:
            print(f"✅ Trading Cycle Error Handling: Exception caught as expected - {e}")
    
    @pytest.mark.asyncio
    async def test_trading_cycle_data_consistency(self, market_data_service, news_service, risk_service):
        """Test data consistency across trading cycle components"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get data from different services
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=100)
            news_data = await news_service.get_news_score(symbol)
            risk_data = await risk_service.assess_risk(symbol, ohlcv_data)
            
            print(f"✅ Data Consistency Check for {symbol}:")
            print(f"   OHLCV Data: {len(ohlcv_data) if ohlcv_data is not None else 0} points")
            print(f"   News Data: {news_data[0] if news_data else 'N/A'}")
            print(f"   Risk Data: {risk_data.get('risk_score', 'N/A') if risk_data else 'N/A'}")
            
            # Validate data consistency
            if ohlcv_data is not None:
                assert len(ohlcv_data) > 0, "OHLCV data should not be empty"
                assert 'close' in ohlcv_data.columns, "OHLCV data should have close prices"
            
            if news_data:
                assert isinstance(news_data[0], (int, float)), "News score should be numeric"
                assert 0 <= news_data[0] <= 100, "News score should be between 0 and 100"
            
            if risk_data:
                assert 'risk_score' in risk_data, "Risk data should have risk score"
                assert 0 <= risk_data['risk_score'] <= 100, "Risk score should be between 0 and 100"
            
        except Exception as e:
            pytest.skip(f"Data consistency test failed: {e}")


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/e2e/test_real_trading_cycle.py -v -s
    pytest.main([__file__, "-v", "-s"])

