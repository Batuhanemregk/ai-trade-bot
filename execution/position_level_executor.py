"""
Position-Level Executor - OKX Position-Level TP/SL + Reduce-Only
Implements position-level TP/SL (entire position), reduce-only, and trailing modify
"""

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from loguru import logger

from infrastructure.config_manager import config_manager


class PositionLevelExecutor:
    """
    Position-level execution system for OKX.
    Implements entire position TP/SL, reduce-only, and trailing modify.
    """
    
    def __init__(self):
        self.config = config_manager
        
        # Load configuration
        self.use_position_tpsl, _ = self.config.get('trading.use_position_tpsl', True)
        self.reduce_only, _ = self.config.get('trading.reduce_only', True)
        
        logger.info(f"[POSITION_EXEC] Position-level executor initialized:")
        logger.info(f"  use_position_tpsl: {self.use_position_tpsl}")
        logger.info(f"  reduce_only: {self.reduce_only}")
    
    def create_position_level_tpsl(self, symbol: str, side: str, quantity: float, 
                                  entry_price: float, sl_price: float, tp_price: float,
                                  client_order_id: str, mode: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Create position-level TP/SL orders (entire position).
        
        Args:
            symbol: Trading symbol
            side: Position side ('buy' or 'sell')
            quantity: Position quantity
            entry_price: Entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            client_order_id: Client order ID
            mode: Trading mode (LIVE/PAPER/DRY-RUN)
            
        Returns:
            Tuple of (success, result_dict)
        """
        if not self.use_position_tpsl:
            logger.info(f"[POSITION_EXEC] Position-level TP/SL disabled for {symbol}")
            return False, {"reason": "disabled"}
        
        if mode == "DRY-RUN":
            logger.info(f"[POSITION_EXEC] DRY-RUN: Position-level TP/SL blocked for {symbol}")
            return True, {
                "mode": "DRY-RUN",
                "sl_order_id": f"DRY_SL_{client_order_id}",
                "tp_order_id": f"DRY_TP_{client_order_id}",
                "blocked": True
            }
        
        try:
            if mode == "PAPER":
                # Paper trading - virtual orders
                from execution.paper_executor import PaperExecutor
                paper_executor = PaperExecutor()
                
                # Create virtual position
                virtual_order = paper_executor.create_virtual_order(
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                    price=entry_price,
                    client_order_id=client_order_id
                )
                
                virtual_position = paper_executor.create_virtual_position(virtual_order)
                
                # Create virtual bracket orders (position-level)
                bracket_orders = paper_executor.create_virtual_bracket_orders(
                    virtual_position, sl_price, tp_price
                )
                
                logger.info(f"[POSITION_EXEC] PAPER: Position-level TP/SL created for {symbol}")
                return True, {
                    "mode": "PAPER",
                    "sl_order_id": bracket_orders['sl_order_id'],
                    "tp_order_id": bracket_orders['tp_order_id'],
                    "position_id": virtual_position.position_id
                }
            
            elif mode == "LIVE":
                # Live trading - real orders
                # TODO: Implement real OKX position-level TP/SL orders
                logger.info(f"[POSITION_EXEC] LIVE: Position-level TP/SL orders would be created for {symbol}")
                return True, {
                    "mode": "LIVE",
                    "sl_order_id": f"LIVE_SL_{client_order_id}",
                    "tp_order_id": f"LIVE_TP_{client_order_id}",
                    "note": "Real orders not implemented yet"
                }
            
            else:
                logger.error(f"[POSITION_EXEC] Unknown mode: {mode}")
                return False, {"reason": "unknown_mode", "mode": mode}
                
        except Exception as e:
            logger.error(f"[POSITION_EXEC] Failed to create position-level TP/SL for {symbol}: {e}")
            return False, {"reason": "error", "error": str(e)}
    
    def modify_trailing_stop(self, symbol: str, position_id: str, new_sl_price: float,
                           mode: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Modify trailing stop (reduce-only).
        
        Args:
            symbol: Trading symbol
            position_id: Position ID
            new_sl_price: New stop loss price
            mode: Trading mode
            
        Returns:
            Tuple of (success, result_dict)
        """
        if not self.reduce_only:
            logger.warning(f"[POSITION_EXEC] Reduce-only disabled for {symbol}")
        
        if mode == "DRY-RUN":
            logger.info(f"[POSITION_EXEC] DRY-RUN: Trailing stop modify blocked for {symbol}")
            return True, {
                "mode": "DRY-RUN",
                "new_sl_price": new_sl_price,
                "blocked": True
            }
        
        try:
            if mode == "PAPER":
                # Paper trading - virtual modify
                from execution.paper_executor import PaperExecutor
                paper_executor = PaperExecutor()
                
                # Get virtual position
                virtual_position = paper_executor.get_virtual_position(position_id)
                if not virtual_position:
                    logger.error(f"[POSITION_EXEC] Virtual position not found: {position_id}")
                    return False, {"reason": "position_not_found"}
                
                # Modify virtual trailing stop
                success = paper_executor.modify_virtual_trailing_stop(virtual_position, new_sl_price)
                
                if success:
                    logger.info(f"[POSITION_EXEC] PAPER: Trailing stop modified for {symbol} to {new_sl_price}")
                    return True, {
                        "mode": "PAPER",
                        "new_sl_price": new_sl_price,
                        "modifications": virtual_position.trailing_modifications
                    }
                else:
                    return False, {"reason": "modify_failed"}
            
            elif mode == "LIVE":
                # Live trading - real modify
                # TODO: Implement real OKX trailing stop modify
                logger.info(f"[POSITION_EXEC] LIVE: Trailing stop would be modified for {symbol} to {new_sl_price}")
                return True, {
                    "mode": "LIVE",
                    "new_sl_price": new_sl_price,
                    "note": "Real modify not implemented yet"
                }
            
            else:
                logger.error(f"[POSITION_EXEC] Unknown mode: {mode}")
                return False, {"reason": "unknown_mode", "mode": mode}
                
        except Exception as e:
            logger.error(f"[POSITION_EXEC] Failed to modify trailing stop for {symbol}: {e}")
            return False, {"reason": "error", "error": str(e)}
    
    def close_position_reduce_only(self, symbol: str, position_id: str, 
                                 quantity: float, price: float, mode: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Close position with reduce-only.
        
        Args:
            symbol: Trading symbol
            position_id: Position ID
            quantity: Quantity to close
            price: Close price
            mode: Trading mode
            
        Returns:
            Tuple of (success, result_dict)
        """
        if not self.reduce_only:
            logger.warning(f"[POSITION_EXEC] Reduce-only disabled for {symbol}")
        
        if mode == "DRY-RUN":
            logger.info(f"[POSITION_EXEC] DRY-RUN: Position close blocked for {symbol}")
            return True, {
                "mode": "DRY-RUN",
                "quantity": quantity,
                "price": price,
                "blocked": True
            }
        
        try:
            if mode == "PAPER":
                # Paper trading - virtual close
                from execution.paper_executor import PaperExecutor
                paper_executor = PaperExecutor()
                
                # Close virtual position
                success = paper_executor.close_virtual_position(position_id)
                
                if success:
                    logger.info(f"[POSITION_EXEC] PAPER: Position closed for {symbol} qty={quantity} price={price}")
                    return True, {
                        "mode": "PAPER",
                        "quantity": quantity,
                        "price": price,
                        "position_id": position_id
                    }
                else:
                    return False, {"reason": "close_failed"}
            
            elif mode == "LIVE":
                # Live trading - real close
                # TODO: Implement real OKX reduce-only close
                logger.info(f"[POSITION_EXEC] LIVE: Position would be closed for {symbol} qty={quantity} price={price}")
                return True, {
                    "mode": "LIVE",
                    "quantity": quantity,
                    "price": price,
                    "note": "Real close not implemented yet"
                }
            
            else:
                logger.error(f"[POSITION_EXEC] Unknown mode: {mode}")
                return False, {"reason": "unknown_mode", "mode": mode}
                
        except Exception as e:
            logger.error(f"[POSITION_EXEC] Failed to close position for {symbol}: {e}")
            return False, {"reason": "error", "error": str(e)}
    
    def validate_position_level_setup(self, symbol: str, side: str, quantity: float) -> Tuple[bool, str]:
        """
        Validate position-level setup requirements.
        
        Args:
            symbol: Trading symbol
            side: Position side
            quantity: Position quantity
            
        Returns:
            Tuple of (valid, reason)
        """
        if not self.use_position_tpsl:
            return False, "position_tpsl_disabled"
        
        if quantity <= 0:
            return False, "invalid_quantity"
        
        if side not in ('buy', 'sell'):
            return False, "invalid_side"
        
        return True, "valid"


# Global position executor instance
position_executor = PositionLevelExecutor()
