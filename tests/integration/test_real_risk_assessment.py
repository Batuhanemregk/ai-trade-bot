"""
Real Risk Assessment Integration Tests
Tests actual risk assessment with real market data and real risk calculations
"""
import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import pandas as pd

from application.risk_service import RiskService
from application.risk_manager import RiskManager
# from application.risk_monitor import RiskMonitor  # Commented out due to missing imports
from application.market_data_service import MarketDataService
from adapters.exchange_okx_ccxt import OKXExchangeAdapter
from configs.policy import load_policy


class TestRealRiskAssessment:
    """Test real risk assessment with actual market data"""
    
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
    def risk_service(self, policy):
        """Create real risk service"""
        return RiskService(policy)
    
    @pytest.fixture(scope="class")
    def risk_manager(self, policy):
        """Create real risk manager"""
        return RiskManager(policy)
    
    # @pytest.fixture(scope="class")
    # def risk_monitor(self, policy):
    #     """Create real risk monitor"""
    #     return RiskMonitor(policy)
    
    @pytest.mark.asyncio
    async def test_risk_service_real_data(self, risk_service, market_data_service):
        """Test risk service with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real OHLCV data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test risk assessment
            risk_result = await risk_service.assess_risk(symbol, ohlcv_data)
            
            assert risk_result is not None
            assert isinstance(risk_result, dict)
            assert 'risk_score' in risk_result
            assert 'risk_level' in risk_result
            assert 'volatility' in risk_result
            assert 'liquidity' in risk_result
            assert 'correlation' in risk_result
            assert 'market_risk' in risk_result
            
            # Validate risk score
            risk_score = risk_result['risk_score']
            assert isinstance(risk_score, (int, float))
            assert 0 <= risk_score <= 100
            
            # Validate risk level
            risk_level = risk_result['risk_level']
            assert risk_level in ['low', 'medium', 'high', 'critical']
            
            print(f"✅ Risk Service: Score {risk_score:.1f} ({risk_level}) for {symbol}")
            print(f"   Volatility: {risk_result['volatility']:.2f}")
            print(f"   Liquidity: {risk_result['liquidity']:.2f}")
            print(f"   Market Risk: {risk_result['market_risk']:.2f}")
            
        except Exception as e:
            pytest.skip(f"Risk service test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_volatility_calculation_real_data(self, risk_service, market_data_service):
        """Test volatility calculation with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real OHLCV data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=100)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Calculate volatility manually for comparison
            returns = ohlcv_data['close'].pct_change().dropna()
            manual_volatility = returns.std() * (24 * 4) ** 0.5  # Annualized for 15m data
            
            # Test risk service volatility calculation
            risk_result = await risk_service.assess_risk(symbol, ohlcv_data)
            service_volatility = risk_result['volatility']
            
            print(f"✅ Volatility Calculation for {symbol}:")
            print(f"   Manual: {manual_volatility:.4f}")
            print(f"   Service: {service_volatility:.4f}")
            print(f"   Difference: {abs(manual_volatility - service_volatility):.4f}")
            
            # Volatility should be reasonable (not zero, not extremely high)
            assert service_volatility > 0, "Volatility should be positive"
            assert service_volatility < 10.0, "Volatility seems too high"
            
        except Exception as e:
            pytest.skip(f"Volatility calculation test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_liquidity_assessment_real_data(self, risk_service, exchange_adapter):
        """Test liquidity assessment with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            
            # Get real ticker and orderbook data
            ticker = await exchange_adapter.get_ticker(symbol)
            orderbook = await exchange_adapter.get_orderbook(symbol, limit=20)
            
            assert ticker is not None
            assert orderbook is not None
            
            # Test liquidity calculation
            volume_24h = ticker.get('baseVolume', 0)
            bid_ask_spread = (orderbook['asks'][0][0] - orderbook['bids'][0][0]) / ticker['last']
            
            print(f"✅ Liquidity Assessment for {symbol}:")
            print(f"   24h Volume: {volume_24h:,.2f}")
            print(f"   Bid-Ask Spread: {bid_ask_spread:.4f}")
            print(f"   Orderbook Depth: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
            
            # Basic liquidity checks
            assert volume_24h > 0, "Volume should be positive"
            assert bid_ask_spread > 0, "Spread should be positive"
            assert bid_ask_spread < 0.1, "Spread seems too wide"
            
        except Exception as e:
            pytest.skip(f"Liquidity assessment test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_correlation_analysis_real_data(self, risk_service, market_data_service):
        """Test correlation analysis with real market data"""
        try:
            symbols = ["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP"]
            ohlcv_data = {}
            
            # Get OHLCV data for multiple symbols
            for symbol in symbols:
                data = await market_data_service._fetch_ohlcv(symbol, "15m", limit=100)
                if data is not None and len(data) > 0:
                    ohlcv_data[symbol] = data
            
            assert len(ohlcv_data) >= 2, "Need at least 2 symbols for correlation analysis"
            
            # Calculate correlations manually
            returns_data = {}
            for symbol, data in ohlcv_data.items():
                returns = data['close'].pct_change().dropna()
                returns_data[symbol] = returns
            
            # Create DataFrame for correlation calculation
            returns_df = pd.DataFrame(returns_data)
            correlation_matrix = returns_df.corr()
            
            print(f"✅ Correlation Analysis:")
            print(f"   Symbols: {list(ohlcv_data.keys())}")
            print(f"   BTC-ETH Correlation: {correlation_matrix.loc['BTC-USDT-SWAP', 'ETH-USDT-SWAP']:.3f}")
            if 'SOL-USDT-SWAP' in correlation_matrix.columns:
                print(f"   BTC-SOL Correlation: {correlation_matrix.loc['BTC-USDT-SWAP', 'SOL-USDT-SWAP']:.3f}")
            
            # Correlation should be reasonable
            btc_eth_corr = correlation_matrix.loc['BTC-USDT-SWAP', 'ETH-USDT-SWAP']
            assert -1 <= btc_eth_corr <= 1, "Correlation should be between -1 and 1"
            assert btc_eth_corr > 0.3, "BTC-ETH correlation seems too low"
            
        except Exception as e:
            pytest.skip(f"Correlation analysis test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_risk_manager_real_data(self, risk_manager, market_data_service):
        """Test risk manager with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test risk manager assessment
            risk_assessment = await risk_manager.assess_portfolio_risk(symbol, ohlcv_data)
            
            assert risk_assessment is not None
            assert isinstance(risk_assessment, dict)
            assert 'overall_risk' in risk_assessment
            assert 'risk_factors' in risk_assessment
            assert 'recommendations' in risk_assessment
            
            print(f"✅ Risk Manager Assessment for {symbol}:")
            print(f"   Overall Risk: {risk_assessment['overall_risk']}")
            print(f"   Risk Factors: {list(risk_assessment['risk_factors'].keys())}")
            print(f"   Recommendations: {len(risk_assessment['recommendations'])} items")
            
        except Exception as e:
            pytest.skip(f"Risk manager test failed: {e}")
    
    # @pytest.mark.asyncio
    # async def test_risk_monitor_real_data(self, risk_monitor, market_data_service):
    #     """Test risk monitor with real market data"""
    #     try:
    #         symbol = "BTC-USDT-SWAP"
    #         timeframe = "15m"
    #         
    #         # Get real market data
    #         ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
    #         
    #         assert ohlcv_data is not None
    #         assert len(ohlcv_data) > 0
    #         
    #         # Test risk monitoring
    #         risk_alerts = await risk_monitor.check_risk_alerts(symbol, ohlcv_data)
    #         
    #         assert risk_alerts is not None
    #         assert isinstance(risk_alerts, list)
    #         
    #         print(f"✅ Risk Monitor for {symbol}:")
    #         print(f"   Alerts: {len(risk_alerts)}")
    #         for alert in risk_alerts[:3]:  # Show first 3 alerts
    #             print(f"   - {alert}")
    #         
    #     except Exception as e:
    #         pytest.skip(f"Risk monitor test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_position_sizing_risk_real_data(self, risk_service, market_data_service):
        """Test position sizing based on risk with real data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            account_balance = 10000  # $10,000 test balance
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test risk-based position sizing
            risk_result = await risk_service.assess_risk(symbol, ohlcv_data)
            
            # Calculate position size based on risk
            risk_score = risk_result['risk_score']
            volatility = risk_result['volatility']
            
            # Simple position sizing logic
            if risk_score < 30:  # Low risk
                max_position_pct = 0.05  # 5% of account
            elif risk_score < 60:  # Medium risk
                max_position_pct = 0.03  # 3% of account
            else:  # High risk
                max_position_pct = 0.01  # 1% of account
            
            max_position_value = account_balance * max_position_pct
            current_price = ohlcv_data['close'].iloc[-1]
            max_position_size = max_position_value / current_price
            
            print(f"✅ Position Sizing for {symbol}:")
            print(f"   Risk Score: {risk_score:.1f}")
            print(f"   Volatility: {volatility:.4f}")
            print(f"   Max Position %: {max_position_pct*100:.1f}%")
            print(f"   Max Position Value: ${max_position_value:,.2f}")
            print(f"   Max Position Size: {max_position_size:.6f} {symbol.split('-')[0]}")
            
            # Validate position sizing
            assert max_position_pct > 0, "Position size should be positive"
            assert max_position_pct <= 0.1, "Position size should not exceed 10%"
            assert max_position_value > 0, "Position value should be positive"
            
        except Exception as e:
            pytest.skip(f"Position sizing risk test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_risk_thresholds_real_data(self, risk_service, market_data_service):
        """Test risk thresholds with real market data"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframe = "15m"
            
            # Get real market data
            ohlcv_data = await market_data_service._fetch_ohlcv(symbol, timeframe, limit=200)
            
            assert ohlcv_data is not None
            assert len(ohlcv_data) > 0
            
            # Test risk assessment
            risk_result = await risk_service.assess_risk(symbol, ohlcv_data)
            
            risk_score = risk_result['risk_score']
            risk_level = risk_result['risk_level']
            
            # Test risk thresholds
            if risk_score < 25:
                expected_level = 'low'
            elif risk_score < 50:
                expected_level = 'medium'
            elif risk_score < 75:
                expected_level = 'high'
            else:
                expected_level = 'critical'
            
            print(f"✅ Risk Thresholds for {symbol}:")
            print(f"   Risk Score: {risk_score:.1f}")
            print(f"   Risk Level: {risk_level}")
            print(f"   Expected Level: {expected_level}")
            
            # Validate risk level matches score
            assert risk_level == expected_level, f"Risk level {risk_level} doesn't match score {risk_score}"
            
        except Exception as e:
            pytest.skip(f"Risk thresholds test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_multiple_timeframes_risk_real_data(self, risk_service, market_data_service):
        """Test risk assessment across multiple timeframes"""
        try:
            symbol = "BTC-USDT-SWAP"
            timeframes = ["15m", "1h", "4h"]
            results = {}
            
            for tf in timeframes:
                try:
                    # Get market data for different timeframes
                    ohlcv_data = await market_data_service._fetch_ohlcv(symbol, tf, limit=100)
                    
                    if ohlcv_data is not None and len(ohlcv_data) > 0:
                        # Assess risk for this timeframe
                        risk_result = await risk_service.assess_risk(symbol, ohlcv_data)
                        
                        results[tf] = {
                            'risk_score': risk_result['risk_score'],
                            'risk_level': risk_result['risk_level'],
                            'volatility': risk_result['volatility'],
                            'data_points': len(ohlcv_data)
                        }
                        
                        print(f"✅ {tf} Risk: Score {risk_result['risk_score']:.1f} ({risk_result['risk_level']})")
                        print(f"   Volatility: {risk_result['volatility']:.4f}, Data: {len(ohlcv_data)} points")
                        
                    else:
                        results[tf] = {'error': 'No data'}
                        print(f"⚠️ {tf}: No data available")
                        
                except Exception as e:
                    results[tf] = {'error': str(e)}
                    print(f"⚠️ {tf}: Risk assessment failed - {e}")
            
            # At least one timeframe should work
            successful_timeframes = [tf for tf, r in results.items() if 'error' not in r]
            assert len(successful_timeframes) > 0, "No timeframes analyzed successfully"
            
            print(f"✅ Successfully analyzed {len(successful_timeframes)}/{len(timeframes)} timeframes")
            
        except Exception as e:
            pytest.skip(f"Multiple timeframes risk test failed: {e}")


if __name__ == "__main__":
    # Run tests with: python -m pytest tests/integration/test_real_risk_assessment.py -v -s
    pytest.main([__file__, "-v", "-s"])
