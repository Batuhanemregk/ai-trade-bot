"""
Test Leverage Limit Enforcement

Tests for the max_leverage enforcement in RiskService.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestLeverageLimit:
    """Tests for leverage limit enforcement."""
    
    @pytest.fixture
    def risk_service_with_policy(self):
        """Create RiskService with leverage policy."""
        from application.risk_service import RiskService
        
        policy = {
            'trading': {
                'risk': {
                    'leverage': {
                        'min_leverage': 1.0,
                        'max_leverage': 5.0,
                        'default': 3.0,
                        'symbol_limits': {
                            'BTC': {'max': 5.0},
                            'ETH': {'max': 5.0},
                            'SOL': {'max': 3.0}
                        }
                    }
                }
            }
        }
        return RiskService(policy)
    
    def test_leverage_within_limits(self, risk_service_with_policy):
        """Test leverage within allowed range passes."""
        should_limit, final_lev, reason, details = risk_service_with_policy.check_leverage_limit(
            requested_leverage=3.0,
            symbol='BTC-USDT-SWAP',
            mode='LIVE'
        )
        
        assert should_limit is False
        assert final_lev == 3.0
        assert reason == 'ok'
    
    def test_leverage_above_max_limited(self, risk_service_with_policy):
        """Test leverage above max is limited down."""
        should_limit, final_lev, reason, details = risk_service_with_policy.check_leverage_limit(
            requested_leverage=10.0,
            symbol='BTC-USDT-SWAP',
            mode='LIVE'
        )
        
        assert should_limit is True
        assert final_lev == 5.0  # BTC max is 5
        assert reason == 'limited_down'
    
    def test_leverage_below_min_limited_up(self, risk_service_with_policy):
        """Test leverage below min is limited up."""
        should_limit, final_lev, reason, details = risk_service_with_policy.check_leverage_limit(
            requested_leverage=0.5,
            symbol='ETH-USDT-SWAP',
            mode='LIVE'
        )
        
        assert should_limit is True
        assert final_lev == 1.0  # min is 1.0
        assert reason == 'limited_up'
    
    def test_symbol_specific_limit(self, risk_service_with_policy):
        """Test symbol-specific leverage limits."""
        # SOL has max 3.0 unlike BTC/ETH with 5.0
        should_limit, final_lev, reason, details = risk_service_with_policy.check_leverage_limit(
            requested_leverage=4.0,
            symbol='SOL-USDT-SWAP',
            mode='LIVE'
        )
        
        assert should_limit is True
        assert final_lev == 3.0  # SOL max is 3.0
        assert reason == 'limited_down'
    
    def test_invalid_leverage_uses_default(self, risk_service_with_policy):
        """Test invalid leverage (0 or negative) uses default."""
        should_limit, final_lev, reason, details = risk_service_with_policy.check_leverage_limit(
            requested_leverage=0,
            symbol='BTC-USDT-SWAP',
            mode='LIVE'
        )
        
        assert should_limit is True
        assert final_lev == 3.0  # default
        assert reason == 'invalid'
    
    def test_leverage_check_with_no_policy(self):
        """Test leverage check with empty policy uses defaults."""
        from application.risk_service import RiskService
        
        risk_service = RiskService({})
        should_limit, final_lev, reason, details = risk_service.check_leverage_limit(
            requested_leverage=3.0,
            symbol='BTC-USDT-SWAP',
            mode='PAPER'
        )
        
        # Should use hardcoded defaults (max=5.0, min=1.0, default=3.0)
        assert final_lev == 3.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
