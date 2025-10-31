"""
Strategy Modes - Single Flip and Scale-In Strategies
Implements single_flip (default) and scale_in (optional) trading strategies
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from loguru import logger

from infrastructure.config_manager import config_manager


@dataclass
class StrategyDecision:
    """Strategy decision result"""
    action: str  # 'enter', 'flip', 'scale_in', 'skip'
    direction: str  # 'LONG', 'SHORT'
    quantity: float
    reason: str
    details: Dict[str, Any]


class StrategyMode:
    """Base strategy mode class"""
    
    def __init__(self):
        self.config = config_manager
    
    def make_decision(self, symbol: str, signal: Dict[str, Any], 
                     current_positions: Dict[str, Any]) -> StrategyDecision:
        """Make trading decision based on strategy"""
        raise NotImplementedError


class SingleFlipStrategy(StrategyMode):
    """
    Single Flip Strategy (default).
    - One open position per symbol
    - No re-entry in same direction
    - Flip on opposite signal
    """
    
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.once_per_bar, _ = self.config.get('trading.strategy.once_per_bar', True)
        self.same_direction_block, _ = self.config.get('trading.strategy.same_direction_block', True)
        self.reversal_enabled, _ = self.config.get('trading.strategy.reversal_enabled', True)
        self.entry_cooldown_bars, _ = self.config.get('trading.entry_cooldown_bars', 2)
        
        logger.info(f"[SINGLE_FLIP] Strategy initialized:")
        logger.info(f"  once_per_bar: {self.once_per_bar}")
        logger.info(f"  same_direction_block: {self.same_direction_block}")
        logger.info(f"  reversal_enabled: {self.reversal_enabled}")
        logger.info(f"  entry_cooldown_bars: {self.entry_cooldown_bars}")
    
    def make_decision(self, symbol: str, signal: Dict[str, Any], 
                     current_positions: Dict[str, Any]) -> StrategyDecision:
        """
        Make single flip strategy decision.
        
        Args:
            symbol: Trading symbol
            signal: Signal dictionary with direction, score, etc.
            current_positions: Current positions dictionary
            
        Returns:
            StrategyDecision
        """
        direction = signal.get('direction', 'FLAT')
        score = signal.get('score', 50.0)
        
        # Check if there's an existing position
        existing_position = current_positions.get(symbol)
        
        if not existing_position:
            # No existing position - can enter
            if direction in ('LONG', 'SHORT'):
                return StrategyDecision(
                    action='enter',
                    direction=direction,
                    quantity=signal.get('quantity', 0.001),
                    reason='new_position',
                    details={
                        'symbol': symbol,
                        'direction': direction,
                        'score': score,
                        'existing_position': None
                    }
                )
            else:
                return StrategyDecision(
                    action='skip',
                    direction=direction,
                    quantity=0.0,
                    reason='no_signal',
                    details={'symbol': symbol, 'direction': direction}
                )
        
        # Existing position - check for flip or block
        existing_direction = existing_position.get('side', '').upper()
        
        if existing_direction == direction.upper():
            # Same direction - block re-entry
            return StrategyDecision(
                action='skip',
                direction=direction,
                quantity=0.0,
                reason='same_direction_block',
                details={
                    'symbol': symbol,
                    'direction': direction,
                    'existing_position': existing_position,
                    'existing_direction': existing_direction
                }
            )
        
        elif self.reversal_enabled and existing_direction != direction.upper():
            # Opposite direction - flip
            return StrategyDecision(
                action='flip',
                direction=direction,
                quantity=signal.get('quantity', 0.001),
                reason='reversal_flip',
                details={
                    'symbol': symbol,
                    'direction': direction,
                    'score': score,
                    'existing_position': existing_position,
                    'existing_direction': existing_direction,
                    'new_direction': direction
                }
            )
        
        else:
            # No flip allowed
            return StrategyDecision(
                action='skip',
                direction=direction,
                quantity=0.0,
                reason='no_flip_allowed',
                details={
                    'symbol': symbol,
                    'direction': direction,
                    'existing_position': existing_position
                }
            )


class ScaleInStrategy(StrategyMode):
    """
    Scale-In Strategy (optional).
    - Add to winning positions only
    - Anti-martingale approach
    - Limited ladders with distance requirements
    """
    
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.max_ladders, _ = self.config.get('trading.strategy.scale_in.max_ladders', 2)
        self.ladder_size_usdt, _ = self.config.get('trading.strategy.scale_in.ladder_size_usdt', 5)
        self.min_dist_pct, _ = self.config.get('trading.strategy.scale_in.min_dist_pct', 0.5)
        self.add_on_profit_only, _ = self.config.get('trading.strategy.scale_in.add_on_profit_only', True)
        
        logger.info(f"[SCALE_IN] Strategy initialized:")
        logger.info(f"  max_ladders: {self.max_ladders}")
        logger.info(f"  ladder_size_usdt: {self.ladder_size_usdt}")
        logger.info(f"  min_dist_pct: {self.min_dist_pct}")
        logger.info(f"  add_on_profit_only: {self.add_on_profit_only}")
    
    def make_decision(self, symbol: str, signal: Dict[str, Any], 
                     current_positions: Dict[str, Any]) -> StrategyDecision:
        """
        Make scale-in strategy decision.
        
        Args:
            symbol: Trading symbol
            signal: Signal dictionary with direction, score, etc.
            current_positions: Current positions dictionary
            
        Returns:
            StrategyDecision
        """
        direction = signal.get('direction', 'FLAT')
        score = signal.get('score', 50.0)
        
        # Check if there's an existing position
        existing_position = current_positions.get(symbol)
        
        if not existing_position:
            # No existing position - can enter
            if direction in ('LONG', 'SHORT'):
                return StrategyDecision(
                    action='enter',
                    direction=direction,
                    quantity=signal.get('quantity', 0.001),
                    reason='new_position',
                    details={
                        'symbol': symbol,
                        'direction': direction,
                        'score': score,
                        'ladder': 1
                    }
                )
            else:
                return StrategyDecision(
                    action='skip',
                    direction=direction,
                    quantity=0.0,
                    reason='no_signal',
                    details={'symbol': symbol, 'direction': direction}
                )
        
        # Existing position - check for scale-in
        existing_direction = existing_position.get('side', '').upper()
        current_price = signal.get('price', 0.0)
        entry_price = existing_position.get('entry_price', 0.0)
        
        if existing_direction != direction.upper():
            # Opposite direction - not allowed in scale-in
            return StrategyDecision(
                action='skip',
                direction=direction,
                quantity=0.0,
                reason='opposite_direction',
                details={
                    'symbol': symbol,
                    'direction': direction,
                    'existing_direction': existing_direction
                }
            )
        
        # Check profit requirement
        if self.add_on_profit_only:
            if existing_direction == 'LONG' and current_price <= entry_price:
                return StrategyDecision(
                    action='skip',
                    direction=direction,
                    quantity=0.0,
                    reason='not_profitable',
                    details={
                        'symbol': symbol,
                        'direction': direction,
                        'current_price': current_price,
                        'entry_price': entry_price
                    }
                )
            elif existing_direction == 'SHORT' and current_price >= entry_price:
                return StrategyDecision(
                    action='skip',
                    direction=direction,
                    quantity=0.0,
                    reason='not_profitable',
                    details={
                        'symbol': symbol,
                        'direction': direction,
                        'current_price': current_price,
                        'entry_price': entry_price
                    }
                )
        
        # Check ladder count
        ladder_count = existing_position.get('ladder_count', 1)
        if ladder_count >= self.max_ladders:
            return StrategyDecision(
                action='skip',
                direction=direction,
                quantity=0.0,
                reason='max_ladders_reached',
                details={
                    'symbol': symbol,
                    'direction': direction,
                    'ladder_count': ladder_count,
                    'max_ladders': self.max_ladders
                }
            )
        
        # Check distance requirement
        price_diff_pct = abs(current_price - entry_price) / entry_price * 100
        if price_diff_pct < self.min_dist_pct:
            return StrategyDecision(
                action='skip',
                direction=direction,
                quantity=0.0,
                reason='insufficient_distance',
                details={
                    'symbol': symbol,
                    'direction': direction,
                    'price_diff_pct': price_diff_pct,
                    'min_dist_pct': self.min_dist_pct
                }
            )
        
        # Scale-in allowed
        return StrategyDecision(
            action='scale_in',
            direction=direction,
            quantity=self.ladder_size_usdt / current_price,  # Convert USDT to quantity
            reason='scale_in_allowed',
            details={
                'symbol': symbol,
                'direction': direction,
                'score': score,
                'ladder': ladder_count + 1,
                'price_diff_pct': price_diff_pct,
                'ladder_size_usdt': self.ladder_size_usdt
            }
        )


class StrategyModeManager:
    """
    Strategy mode manager.
    Manages strategy selection and execution.
    """
    
    def __init__(self):
        self.config = config_manager
        self.strategies = {
            'single_flip': SingleFlipStrategy(),
            'scale_in': ScaleInStrategy()
        }
        
        # Load current strategy
        self.current_strategy_type, _ = self.config.get('trading.strategy.type', 'single_flip')
        self.current_strategy = self.strategies.get(self.current_strategy_type, self.strategies['single_flip'])
        
        logger.info(f"[STRATEGY_MANAGER] Strategy mode manager initialized:")
        logger.info(f"  current_strategy: {self.current_strategy_type}")
        logger.info(f"  available_strategies: {list(self.strategies.keys())}")
    
    def get_strategy(self) -> StrategyMode:
        """Get current strategy"""
        return self.current_strategy
    
    def make_decision(self, symbol: str, signal: Dict[str, Any], 
                     current_positions: Dict[str, Any]) -> StrategyDecision:
        """
        Make strategy decision using current strategy.
        
        Args:
            symbol: Trading symbol
            signal: Signal dictionary
            current_positions: Current positions dictionary
            
        Returns:
            StrategyDecision
        """
        return self.current_strategy.make_decision(symbol, signal, current_positions)
    
    def switch_strategy(self, strategy_type: str) -> bool:
        """
        Switch to different strategy.
        
        Args:
            strategy_type: Strategy type ('single_flip' or 'scale_in')
            
        Returns:
            True if switched successfully
        """
        if strategy_type in self.strategies:
            self.current_strategy_type = strategy_type
            self.current_strategy = self.strategies[strategy_type]
            logger.info(f"[STRATEGY_MANAGER] Switched to strategy: {strategy_type}")
            return True
        else:
            logger.error(f"[STRATEGY_MANAGER] Unknown strategy type: {strategy_type}")
            return False


# Global strategy manager instance
strategy_manager = StrategyModeManager()
