"""
Unit tests for Backtest Virtual Exchange.

Tests TP/SL hit detection for long/short positions and tie-break modes.
"""

import pytest
from datetime import datetime
from backtest.virtual_exchange import VirtualExchangeAdapter, VirtualPosition, IntrabarMode


class TestTPSLHitDetection:
    """Tests for TP/SL hit detection logic."""
    
    def setup_method(self):
        """Setup for each test."""
        self.exchange = VirtualExchangeAdapter(
            fee_bps=0,  # No fees for testing
            slippage_bps=0,  # No slippage for testing
            intrabar_mode=IntrabarMode.CONSERVATIVE
        )
        self.exchange.set_initial_balance(10000)
        self.exchange.set_bar_context(0, datetime.now())
    
    def test_long_tp_hit(self):
        """Test TP hit for long position."""
        # Open long at 100, TP at 110, SL at 95
        self.exchange.open_position(
            symbol="TEST", side="long", size_usdt=100,
            price=100, tp_price=110, sl_price=95
        )
        
        # Bar where high reaches TP
        result = self.exchange.check_tpsl_hit("TEST", bar_high=112, bar_low=98, bar_close=105)
        assert result == "TP_HIT"
    
    def test_long_sl_hit(self):
        """Test SL hit for long position."""
        self.exchange.open_position(
            symbol="TEST", side="long", size_usdt=100,
            price=100, tp_price=110, sl_price=95
        )
        
        # Bar where low reaches SL
        result = self.exchange.check_tpsl_hit("TEST", bar_high=102, bar_low=93, bar_close=94)
        assert result == "SL_HIT"
    
    def test_long_no_hit(self):
        """Test neither TP nor SL hit for long."""
        self.exchange.open_position(
            symbol="TEST", side="long", size_usdt=100,
            price=100, tp_price=110, sl_price=95
        )
        
        # Bar within TP/SL range
        result = self.exchange.check_tpsl_hit("TEST", bar_high=105, bar_low=97, bar_close=102)
        assert result is None
    
    def test_short_tp_hit(self):
        """Test TP hit for short position."""
        self.exchange.open_position(
            symbol="TEST", side="short", size_usdt=100,
            price=100, tp_price=90, sl_price=105
        )
        
        # Bar where low reaches TP (for short, TP is lower)
        result = self.exchange.check_tpsl_hit("TEST", bar_high=98, bar_low=88, bar_close=89)
        assert result == "TP_HIT"
    
    def test_short_sl_hit(self):
        """Test SL hit for short position."""
        self.exchange.open_position(
            symbol="TEST", side="short", size_usdt=100,
            price=100, tp_price=90, sl_price=105
        )
        
        # Bar where high reaches SL (for short, SL is higher)
        result = self.exchange.check_tpsl_hit("TEST", bar_high=107, bar_low=99, bar_close=106)
        assert result == "SL_HIT"
    
    def test_short_no_hit(self):
        """Test neither TP nor SL hit for short."""
        self.exchange.open_position(
            symbol="TEST", side="short", size_usdt=100,
            price=100, tp_price=90, sl_price=105
        )
        
        # Bar within TP/SL range
        result = self.exchange.check_tpsl_hit("TEST", bar_high=103, bar_low=93, bar_close=97)
        assert result is None


class TestIntrabarTieBreak:
    """Tests for intrabar tie-break modes."""
    
    def test_conservative_mode_sl_wins(self):
        """Test conservative mode: SL wins when both hit."""
        exchange = VirtualExchangeAdapter(
            fee_bps=0, slippage_bps=0,
            intrabar_mode=IntrabarMode.CONSERVATIVE
        )
        exchange.set_initial_balance(10000)
        exchange.set_bar_context(0, datetime.now())
        
        # Long position
        exchange.open_position(
            symbol="TEST", side="long", size_usdt=100,
            price=100, tp_price=110, sl_price=95
        )
        
        # Bar where BOTH TP and SL are hit (high >= 110, low <= 95)
        result = exchange.check_tpsl_hit("TEST", bar_high=115, bar_low=90, bar_close=100)
        assert result == "SL_HIT", "Conservative mode should prefer SL"
    
    def test_optimistic_mode_tp_wins(self):
        """Test optimistic mode: TP wins when both hit."""
        exchange = VirtualExchangeAdapter(
            fee_bps=0, slippage_bps=0,
            intrabar_mode=IntrabarMode.OPTIMISTIC
        )
        exchange.set_initial_balance(10000)
        exchange.set_bar_context(0, datetime.now())
        
        # Long position
        exchange.open_position(
            symbol="TEST", side="long", size_usdt=100,
            price=100, tp_price=110, sl_price=95
        )
        
        # Bar where BOTH TP and SL are hit
        result = exchange.check_tpsl_hit("TEST", bar_high=115, bar_low=90, bar_close=100)
        assert result == "TP_HIT", "Optimistic mode should prefer TP"
    
    def test_conservative_short_sl_wins(self):
        """Test conservative mode for short: SL wins when both hit."""
        exchange = VirtualExchangeAdapter(
            fee_bps=0, slippage_bps=0,
            intrabar_mode=IntrabarMode.CONSERVATIVE
        )
        exchange.set_initial_balance(10000)
        exchange.set_bar_context(0, datetime.now())
        
        # Short position: TP at 90, SL at 105
        exchange.open_position(
            symbol="TEST", side="short", size_usdt=100,
            price=100, tp_price=90, sl_price=105
        )
        
        # Bar where BOTH TP and SL are hit (high >= 105, low <= 90)
        result = exchange.check_tpsl_hit("TEST", bar_high=110, bar_low=85, bar_close=95)
        assert result == "SL_HIT", "Conservative mode should prefer SL for short"


class TestPositionManagement:
    """Tests for position opening/closing."""
    
    def setup_method(self):
        """Setup for each test."""
        self.exchange = VirtualExchangeAdapter(
            fee_bps=6,  # 0.06% fee
            slippage_bps=3,  # 0.03% slippage
            intrabar_mode=IntrabarMode.CONSERVATIVE
        )
        self.exchange.set_initial_balance(10000)
        self.exchange.set_bar_context(0, datetime.now())
    
    def test_open_close_long_profit(self):
        """Test opening and closing long position with profit."""
        # Open long at 100
        self.exchange.open_position(
            symbol="TEST", side="long", size_usdt=100,
            price=100, tp_price=110, sl_price=95
        )
        
        assert self.exchange.has_position("TEST")
        
        # Close at 105 (5% profit)
        self.exchange.set_bar_context(1, datetime.now())
        trade = self.exchange.close_position("TEST", 105, "SIGNAL_EXIT")
        
        assert trade is not None
        assert trade.side == "long"
        assert trade.pnl_pct > 0  # Profitable
        assert not self.exchange.has_position("TEST")
    
    def test_open_close_short_profit(self):
        """Test opening and closing short position with profit."""
        # Open short at 100
        self.exchange.open_position(
            symbol="TEST", side="short", size_usdt=100,
            price=100, tp_price=90, sl_price=105
        )
        
        assert self.exchange.has_position("TEST")
        
        # Close at 95 (5% profit for short)
        self.exchange.set_bar_context(1, datetime.now())
        trade = self.exchange.close_position("TEST", 95, "SIGNAL_EXIT")
        
        assert trade is not None
        assert trade.side == "short"
        assert trade.pnl_pct > 0  # Profitable
    
    def test_fee_deduction(self):
        """Test that fees are deducted correctly."""
        initial_balance = self.exchange.balance
        
        # Open position (fee on entry)
        self.exchange.open_position(
            symbol="TEST", side="long", size_usdt=100,
            price=100, tp_price=110, sl_price=95
        )
        
        # Balance should be reduced by entry fee
        assert self.exchange.balance < initial_balance
        
        # Close position (fee on exit)
        self.exchange.set_bar_context(1, datetime.now())
        self.exchange.close_position("TEST", 100, "SIGNAL_EXIT")  # Break-even price
        
        # Should have lost money due to fees (no price gain)
        assert self.exchange.balance < initial_balance


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
