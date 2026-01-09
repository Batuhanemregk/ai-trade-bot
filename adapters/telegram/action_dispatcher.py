"""
Telegram Action Dispatcher - Handles action callbacks and executes real operations.
Routes ai:act|t=<type>|... callbacks to appropriate handlers.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
from loguru import logger


@dataclass
class ActionResult:
    """Result of an action execution."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    next_view: Optional[str] = None  # View to navigate to after action


class ActionDispatcher:
    """
    Dispatches Telegram callback actions to real operations.
    
    Callback Schema: ai:act|t=<action_type>|s=<symbol>|...params
    
    Supported Actions:
    - close: Close position
    - edit_sl: Edit stop loss
    - edit_tp: Edit take profit
    - cancel: Cancel order
    - refresh: Refresh current view
    - toggle: Toggle setting
    - emergency: Emergency stop all
    """
    
    def __init__(self):
        self.logger = logger.bind(component="action_dispatcher")
        self._exchange_adapter = None
        self._policy = None
        
        # Action handlers map
        self._handlers = {
            'close': self._handle_close_position,
            'edit_sl': self._handle_edit_sl,
            'edit_tp': self._handle_edit_tp,
            'cancel': self._handle_cancel_order,
            'refresh': self._handle_refresh,
            'toggle': self._handle_toggle_setting,
            'emergency': self._handle_emergency_stop,
            'set_sl': self._handle_set_sl_preset,
            'set_tp': self._handle_set_tp_preset,
            'set_lev': self._handle_set_leverage,
            'restart': self._handle_restart_bot,
            # Advanced settings handlers
            'set_min_size': self._handle_set_min_size,
            'set_max_size': self._handle_set_max_size,
            'add_coin': self._handle_add_coin,
            'remove_coin': self._handle_remove_coin,
            'set_thresh': self._handle_set_threshold,
            'adj_thresh': self._handle_adjust_threshold,  # Threshold preview
            'save_thresh': self._handle_save_thresholds,  # Save pending thresholds
            'cancel_thresh': self._handle_cancel_thresholds,  # Cancel pending thresholds
            'set_age': self._handle_set_age,
            'set_weight': self._handle_set_weight,
            'adj_weight': self._handle_adjust_weight,  # Score weight preview
            'save_weights': self._handle_save_weights,  # Save pending weights
            'cancel_weights': self._handle_cancel_weights,  # Cancel pending weights
            'set_preset': self._handle_set_preset,
            'toggle_mlboost': self._handle_toggle_mlboost,
            'set_ml_tier': self._handle_set_ml_tier,
            'set_atr': self._handle_set_atr,  # ATR TP/SL adjustment
            'adj_atr': self._handle_adjust_atr,  # ATR preview mode
            'save_atr': self._handle_save_atr,  # Save pending ATR
            'cancel_atr': self._handle_cancel_atr,  # Cancel pending ATR
            # Tier-based position sizing handlers
            'adj_tier': self._handle_adjust_tier,
            'save_tiers': self._handle_save_tiers,
            'cancel_tiers': self._handle_cancel_tiers,
            # Signal history handlers
            'clear_sig': self._handle_clear_signal_history,
            'clear_all_sig': self._handle_clear_all_signals,
            # Alert history handlers
            'clear_alerts': self._handle_clear_alerts,
            # Trading control
            'toggle_trading': self._handle_toggle_trading,
            # Trailing stop handlers
            'trail_preset': self._handle_trail_preset,
            'trail_adj': self._handle_trail_adjust,
            'save_trail': self._handle_save_trail,
            'cancel_trail': self._handle_cancel_trail,
        }
        
        # Session states for pending adjustments
        self._pending_tiers: Dict[str, float] = {}
        self._pending_weights: Dict[str, float] = {}
        self._pending_atr: Dict[str, float] = {}
        self._pending_thresh: Dict[str, int] = {}
        self._pending_trail: Dict[str, float] = {}
    
    def _get_exchange_adapter(self):
        """Lazy load exchange adapter."""
        if self._exchange_adapter is None:
            try:
                from adapters.exchange_okx_ccxt import OKXCCXTAdapter
                self._exchange_adapter = OKXCCXTAdapter()
            except Exception as e:
                self.logger.error(f"Failed to create exchange adapter: {e}")
        return self._exchange_adapter
    
    def _get_policy(self) -> Dict:
        """Lazy load policy."""
        if self._policy is None:
            try:
                from infrastructure.bootstrap import load_policy
                self._policy = load_policy()
            except Exception as e:
                self.logger.warning(f"Failed to load policy: {e}")
                self._policy = {}
        return self._policy
    
    # Symbols to ignore (not touch)
    IGNORED_SYMBOLS = ['MINA', 'MINA-USDT-SWAP', 'MINA/USDT:USDT']
    
    def needs_confirmation(self, action_type: str) -> bool:
        """
        Check if an action type requires confirmation.
        
        Args:
            action_type: The action type to check
            
        Returns:
            True if confirmation is required
        """
        # Actions that require confirmation
        confirmation_actions = ['close', 'emergency', 'cancel']
        return action_type in confirmation_actions
    
    def is_symbol_ignored(self, symbol: str) -> bool:
        """Check if a symbol should be ignored."""
        if not symbol:
            return False
        base = symbol.split('-')[0].split('/')[0].upper()
        return base in ['MINA'] or symbol in self.IGNORED_SYMBOLS

    async def dispatch(self, action_type: str, params: Dict[str, Any]) -> ActionResult:
        """
        Dispatch action to appropriate handler.
        
        Args:
            action_type: Action type (close, edit_sl, etc.)
            params: Action parameters
            
        Returns:
            ActionResult with success status and message
        """
        self.logger.info(f"[ACTION] Dispatching: type={action_type} params={params}")
        
        handler = self._handlers.get(action_type)
        if not handler:
            return ActionResult(
                success=False,
                message=f"Unknown action: {action_type}",
                error="UNKNOWN_ACTION"
            )
        
        try:
            result = await handler(params)
            self.logger.info(f"[ACTION] Result: {result.success} - {result.message}")
            return result
        except Exception as e:
            self.logger.error(f"[ACTION] Error in {action_type}: {e}", exc_info=True)
            return ActionResult(
                success=False,
                message=f"Action failed: {str(e)[:50]}",
                error=str(e)
            )
    
    async def _handle_close_position(self, params: Dict) -> ActionResult:
        """
        Close a position.
        
        Params:
            s: Symbol (e.g., BTC, ETH)
            c: Confirmed (1 = execute, 0 = show confirm)
        """
        symbol = params.get('s', '')
        confirmed = params.get('c', '0') == '1'
        
        if not symbol:
            return ActionResult(False, "Symbol required", error="MISSING_SYMBOL")
        
        # Normalize symbol
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        exchange = self._get_exchange_adapter()
        if not exchange:
            return ActionResult(False, "Exchange unavailable", error="NO_EXCHANGE")
        
        if not confirmed:
            # Return info for confirmation dialog
            try:
                positions = await exchange.fetch_positions()
                pos = next((p for p in positions if symbol in p.get('symbol', '')), None)
                
                if not pos:
                    return ActionResult(False, f"No position found for {symbol}", error="NO_POSITION")
                
                pos_data = {
                    'symbol': symbol,
                    'side': pos.get('side', 'unknown'),
                    'size': float(pos.get('contracts', 0)),
                    'entry': float(pos.get('avgPrice', 0)),
                    'mark': float(pos.get('markPrice', 0)),
                    'upnl': float(pos.get('unrealizedPnl', 0)),
                }
                
                return ActionResult(
                    success=True,
                    message="Confirm close position",
                    data={'position': pos_data, 'needs_confirm': True},
                    next_view='confirm_close'
                )
            except Exception as e:
                return ActionResult(False, f"Failed to get position: {e}", error=str(e))
        
        # Execute close
        try:
            # Get position details
            positions = await exchange.fetch_positions()
            pos = next((p for p in positions if symbol in p.get('symbol', '')), None)
            
            if not pos:
                return ActionResult(False, f"No position to close for {symbol}", error="NO_POSITION")
            
            size = abs(float(pos.get('contracts', 0)))
            side = pos.get('side', 'long')
            
            # Close by placing opposite market order
            close_side = 'sell' if side == 'long' else 'buy'
            
            order = await exchange.create_market_order(
                symbol=symbol,
                side=close_side,
                amount=size,
                params={'reduceOnly': True}
            )
            
            self.logger.info(f"[CLOSE] Position closed: {symbol} {side} {size}")
            
            return ActionResult(
                success=True,
                message=f"✅ Position closed: {symbol}",
                data={'order': order},
                next_view='positions'
            )
        except Exception as e:
            self.logger.error(f"[CLOSE] Failed: {e}")
            return ActionResult(False, f"Failed to close: {str(e)[:50]}", error=str(e))
    
    async def _handle_edit_sl(self, params: Dict) -> ActionResult:
        """Edit stop loss for a position."""
        symbol = params.get('s', '')
        new_sl = params.get('v', '')
        
        if not symbol or not new_sl:
            return ActionResult(False, "Symbol and value required", error="MISSING_PARAMS")
        
        try:
            new_sl = float(new_sl)
        except ValueError:
            return ActionResult(False, "Invalid SL value", error="INVALID_VALUE")
        
        # Normalize symbol
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        exchange = self._get_exchange_adapter()
        if not exchange:
            return ActionResult(False, "Exchange unavailable", error="NO_EXCHANGE")
        
        try:
            # Get current position
            positions = await exchange.fetch_positions()
            pos = next((p for p in positions if symbol in p.get('symbol', '')), None)
            
            if not pos:
                return ActionResult(False, f"No position for {symbol}", error="NO_POSITION")
            
            size = abs(float(pos.get('contracts', 0)))
            side = pos.get('side', 'long')
            
            # Cancel existing SL orders and place new one
            # First, fetch algo orders
            from adapters.exchange_okx_rest import OKXRESTAdapter
            rest_adapter = OKXRESTAdapter()
            
            # Cancel existing SL
            await rest_adapter.cancel_algo_orders(symbol, order_type='conditional')
            
            # Place new SL
            sl_side = 'sell' if side == 'long' else 'buy'
            await rest_adapter.place_stop_loss(
                symbol=symbol,
                side=sl_side,
                size=size,
                trigger_price=new_sl,
                reduce_only=True
            )
            
            return ActionResult(
                success=True,
                message=f"✅ SL updated to ${new_sl:,.2f}",
                next_view='tpsl'
            )
        except Exception as e:
            return ActionResult(False, f"Failed to update SL: {str(e)[:50]}", error=str(e))
    
    async def _handle_edit_tp(self, params: Dict) -> ActionResult:
        """Edit take profit for a position."""
        symbol = params.get('s', '')
        new_tp = params.get('v', '')
        
        if not symbol or not new_tp:
            return ActionResult(False, "Symbol and value required", error="MISSING_PARAMS")
        
        try:
            new_tp = float(new_tp)
        except ValueError:
            return ActionResult(False, "Invalid TP value", error="INVALID_VALUE")
        
        # Normalize symbol
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        exchange = self._get_exchange_adapter()
        if not exchange:
            return ActionResult(False, "Exchange unavailable", error="NO_EXCHANGE")
        
        try:
            # Get current position
            positions = await exchange.fetch_positions()
            pos = next((p for p in positions if symbol in p.get('symbol', '')), None)
            
            if not pos:
                return ActionResult(False, f"No position for {symbol}", error="NO_POSITION")
            
            size = abs(float(pos.get('contracts', 0)))
            side = pos.get('side', 'long')
            
            # Cancel existing TP orders and place new one
            from adapters.exchange_okx_rest import OKXRESTAdapter
            rest_adapter = OKXRESTAdapter()
            
            # Cancel existing TP
            await rest_adapter.cancel_algo_orders(symbol, order_type='conditional')
            
            # Place new TP
            tp_side = 'sell' if side == 'long' else 'buy'
            await rest_adapter.place_take_profit(
                symbol=symbol,
                side=tp_side,
                size=size,
                trigger_price=new_tp,
                reduce_only=True
            )
            
            return ActionResult(
                success=True,
                message=f"✅ TP updated to ${new_tp:,.2f}",
                next_view='tpsl'
            )
        except Exception as e:
            return ActionResult(False, f"Failed to update TP: {str(e)[:50]}", error=str(e))
    
    async def _handle_set_sl_preset(self, params: Dict) -> ActionResult:
        """Set SL using percentage preset."""
        symbol = params.get('s', '')
        pct = params.get('pct', '')
        
        if not symbol or not pct:
            return ActionResult(False, "Symbol and percentage required", error="MISSING_PARAMS")
        
        try:
            pct = float(pct)
        except ValueError:
            return ActionResult(False, "Invalid percentage", error="INVALID_VALUE")
        
        # Normalize symbol
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        exchange = self._get_exchange_adapter()
        if not exchange:
            return ActionResult(False, "Exchange unavailable", error="NO_EXCHANGE")
        
        try:
            # Get current position entry price
            positions = await exchange.fetch_positions()
            pos = next((p for p in positions if symbol in p.get('symbol', '')), None)
            
            if not pos:
                return ActionResult(False, f"No position for {symbol}", error="NO_POSITION")
            
            entry = float(pos.get('avgPrice', 0))
            side = pos.get('side', 'long')
            
            # Calculate SL price
            if side == 'long':
                new_sl = entry * (1 + pct / 100)  # pct is negative for long SL
            else:
                new_sl = entry * (1 - pct / 100)  # pct is negative for short SL
            
            # Use edit_sl handler
            return await self._handle_edit_sl({'s': symbol.replace('-USDT-SWAP', ''), 'v': str(new_sl)})
            
        except Exception as e:
            return ActionResult(False, f"Failed: {str(e)[:50]}", error=str(e))
    
    async def _handle_set_tp_preset(self, params: Dict) -> ActionResult:
        """Set TP using percentage preset."""
        symbol = params.get('s', '')
        pct = params.get('pct', '')
        
        if not symbol or not pct:
            return ActionResult(False, "Symbol and percentage required", error="MISSING_PARAMS")
        
        try:
            pct = float(pct)
        except ValueError:
            return ActionResult(False, "Invalid percentage", error="INVALID_VALUE")
        
        # Normalize symbol
        if not symbol.endswith('-USDT-SWAP'):
            symbol = f"{symbol}-USDT-SWAP"
        
        exchange = self._get_exchange_adapter()
        if not exchange:
            return ActionResult(False, "Exchange unavailable", error="NO_EXCHANGE")
        
        try:
            # Get current position entry price
            positions = await exchange.fetch_positions()
            pos = next((p for p in positions if symbol in p.get('symbol', '')), None)
            
            if not pos:
                return ActionResult(False, f"No position for {symbol}", error="NO_POSITION")
            
            entry = float(pos.get('avgPrice', 0))
            side = pos.get('side', 'long')
            
            # Calculate TP price
            if side == 'long':
                new_tp = entry * (1 + pct / 100)  # pct is positive for long TP
            else:
                new_tp = entry * (1 - pct / 100)  # pct is positive for short TP
            
            # Use edit_tp handler
            return await self._handle_edit_tp({'s': symbol.replace('-USDT-SWAP', ''), 'v': str(new_tp)})
            
        except Exception as e:
            return ActionResult(False, f"Failed: {str(e)[:50]}", error=str(e))
    
    async def _handle_cancel_order(self, params: Dict) -> ActionResult:
        """Cancel a pending order."""
        order_id = params.get('id', '')
        symbol = params.get('s', '')
        confirmed = params.get('c', '0') == '1'
        
        if not order_id:
            return ActionResult(False, "Order ID required", error="MISSING_ORDER_ID")
        
        exchange = self._get_exchange_adapter()
        if not exchange:
            return ActionResult(False, "Exchange unavailable", error="NO_EXCHANGE")
        
        if not confirmed:
            # Return confirmation needed
            return ActionResult(
                success=True,
                message="Confirm cancel order",
                data={'order_id': order_id, 'symbol': symbol, 'needs_confirm': True},
                next_view='confirm_cancel'
            )
        
        try:
            await exchange.cancel_order(order_id, symbol)
            
            return ActionResult(
                success=True,
                message=f"✅ Order cancelled: {order_id[:8]}...",
                next_view='orders'
            )
        except Exception as e:
            return ActionResult(False, f"Failed to cancel: {str(e)[:50]}", error=str(e))
    
    async def _handle_refresh(self, params: Dict) -> ActionResult:
        """Refresh current view (clears cache)."""
        view = params.get('v', 'main')
        
        # Clear cache for this view
        try:
            from adapters.telegram.context_resolver import get_context_resolver
            resolver = get_context_resolver()
            
            # Clear relevant cache keys
            cache_keys_to_clear = []
            if view == 'positions' or view == 'current':
                cache_keys_to_clear.extend(['positions:all', 'pnl'])
            elif view == 'signals':
                cache_keys_to_clear.extend(['signals:6:all', 'signals:3:all'])
            elif view == 'orders':
                cache_keys_to_clear.append('orders')
            
            for key in cache_keys_to_clear:
                if key in resolver._data_cache:
                    del resolver._data_cache[key]
            
            return ActionResult(
                success=True,
                message="🔄 Refreshed",
                next_view=view if view != 'current' else None
            )
        except Exception as e:
            return ActionResult(
                success=True,  # Still success, just couldn't clear cache
                message="🔄 Refreshed",
                next_view=view if view != 'current' else None
            )
    
    async def _handle_toggle_setting(self, params: Dict) -> ActionResult:
        """Toggle a user setting or trading feature."""
        setting_key = params.get('k', '')
        user_id = params.get('u', None)
        
        if not setting_key:
            return ActionResult(False, "Setting key required", error="MISSING_KEY")
        
        # Trading feature toggles - these update policy.yaml
        trading_features = ['trailing', 'partial_tp', 'time_exit', 'dynamic_tpsl']
        
        if setting_key in trading_features:
            return await self._toggle_trading_feature(setting_key)
        
        # User settings toggles (compact, emojis, etc.)
        try:
            from adapters.telegram.user_settings import get_user_settings
            settings = get_user_settings()
            
            # Get current value and toggle
            current = settings.get(user_id, setting_key, default=False)
            new_value = not current
            settings.set(user_id, setting_key, new_value)
            
            status = "ON ✅" if new_value else "OFF ❌"
            return ActionResult(
                success=True,
                message=f"{setting_key}: {status}",
                data={'key': setting_key, 'value': new_value},
                next_view='settings'
            )
        except Exception as e:
            return ActionResult(False, f"Failed: {str(e)[:50]}", error=str(e))
    
    async def _toggle_trading_feature(self, feature: str) -> ActionResult:
        """Toggle a trading feature in policy.yaml."""
        try:
            import yaml
            import os
            
            policy_path = os.path.join(os.getcwd(), 'configs', 'policy.yaml')
            
            # Load current policy
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy = yaml.safe_load(f)
            
            # Features are directly under 'trading', not 'trading.scoring'
            trading = policy.get('trading', {})
            
            # Map feature name to config location (directly under trading)
            feature_configs = {
                'trailing': trading.get('trailing', {}),
                'partial_tp': trading.get('partial_tp', {}),
                'time_exit': trading.get('time_exit', {}),
                'dynamic_tpsl': trading.get('dynamic_tpsl', {}),
            }
            
            if feature not in feature_configs:
                return ActionResult(False, f"Unknown feature: {feature}", error="UNKNOWN_FEATURE")
            
            feature_config = feature_configs[feature]
            current = feature_config.get('enabled', False)
            new_value = not current
            
            # Update the value directly in trading section
            if feature not in trading:
                trading[feature] = {}
            trading[feature]['enabled'] = new_value
            
            # Save policy
            with open(policy_path, 'w', encoding='utf-8') as f:
                yaml.dump(policy, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Clear policy cache
            self._policy = None
            
            status = "ON ✅" if new_value else "OFF ❌"
            feature_names = {
                'trailing': '📈 Trailing Stop',
                'partial_tp': '💰 Partial TP',
                'time_exit': '⏰ Time Exit',
                'dynamic_tpsl': '📊 Dynamic TP/SL',
            }
            
            self.logger.info(f"[TOGGLE] {feature} set to {new_value}")
            
            return ActionResult(
                success=True,
                message=f"{feature_names.get(feature, feature)}: {status}\n\n⚠️ Restart gerektirir",
                data={'feature': feature, 'enabled': new_value},
                next_view='settings'
            )
            
        except Exception as e:
            self.logger.error(f"[TOGGLE] Failed to toggle {feature}: {e}")
            return ActionResult(False, f"Failed: {str(e)[:50]}", error=str(e))
    
    async def _handle_set_leverage(self, params: Dict) -> ActionResult:
        """Set leverage value in policy.yaml (requires restart)."""
        # Callback registry expands 'v' to 'view', so check both
        value = params.get('view', params.get('v', ''))
        
        if not value:
            return ActionResult(False, "Leverage value required", error="MISSING_VALUE")
        
        try:
            import yaml
            import os
            
            leverage = int(value)
            
            # Get limits from policy
            policy = self._get_policy()
            leverage_config = policy.get('trading', {}).get('risk', {}).get('leverage', {})
            min_lev = leverage_config.get('min_leverage', 1)
            max_lev = leverage_config.get('max_leverage', 10)
            
            # Clamp to limits
            leverage = max(min_lev, min(max_lev, leverage))
            
            # Save to policy.yaml
            policy_path = os.path.join(os.getcwd(), 'configs', 'policy.yaml')
            
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            
            # Update leverage in policy
            if 'trading' not in policy_data:
                policy_data['trading'] = {}
            if 'risk' not in policy_data['trading']:
                policy_data['trading']['risk'] = {}
            if 'leverage' not in policy_data['trading']['risk']:
                policy_data['trading']['risk']['leverage'] = {}
            
            policy_data['trading']['risk']['leverage']['default'] = leverage
            
            with open(policy_path, 'w', encoding='utf-8') as f:
                yaml.dump(policy_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Clear policy cache
            self._policy = None
            
            self.logger.info(f"[LEVERAGE] Set leverage to {leverage}x in policy.yaml")
            
            return ActionResult(
                success=True,
                message=f"⚡ Leverage: {leverage}x\n\n⚠️ Restart gerektirir",
                data={'leverage': leverage},
                next_view='settings'
            )
        except Exception as e:
            return ActionResult(False, f"Failed: {str(e)[:50]}", error=str(e))
    
    async def _handle_emergency_stop(self, params: Dict) -> ActionResult:
        """
        Emergency stop: Close all positions and cancel all orders.
        
        Params:
            code: Confirmation code (must match generated code)
        """
        code = params.get('code', '')
        
        if not code:
            # Generate confirmation code and show dialog
            import random
            confirm_code = str(random.randint(1000, 9999))
            
            return ActionResult(
                success=True,
                message="⚠️ Emergency Stop requires confirmation",
                data={'confirm_code': confirm_code, 'needs_confirm': True},
                next_view='emergency_confirm'
            )
        
        # Execute emergency stop
        exchange = self._get_exchange_adapter()
        if not exchange:
            return ActionResult(False, "Exchange unavailable", error="NO_EXCHANGE")
        
        try:
            results = {
                'positions_closed': 0,
                'orders_cancelled': 0,
                'errors': []
            }
            
            # Close all positions
            positions = await exchange.fetch_positions()
            for pos in positions:
                size = float(pos.get('contracts', 0))
                if size == 0:
                    continue
                
                symbol = pos.get('symbol', '')
                side = pos.get('side', 'long')
                close_side = 'sell' if side == 'long' else 'buy'
                
                try:
                    await exchange.create_market_order(
                        symbol=symbol,
                        side=close_side,
                        amount=abs(size),
                        params={'reduceOnly': True}
                    )
                    results['positions_closed'] += 1
                except Exception as e:
                    results['errors'].append(f"{symbol}: {str(e)[:30]}")
            
            # Cancel all orders
            try:
                open_orders = await exchange.fetch_open_orders()
                for order in open_orders:
                    try:
                        await exchange.cancel_order(order['id'], order['symbol'])
                        results['orders_cancelled'] += 1
                    except Exception as e:
                        results['errors'].append(f"Order {order['id'][:8]}: {str(e)[:20]}")
            except Exception as e:
                results['errors'].append(f"Orders: {str(e)[:30]}")
            
            # Activate circuit breaker
            try:
                from application.circuit_breaker import get_circuit_breaker
                cb = get_circuit_breaker()
                cb.trigger_emergency("TELEGRAM_EMERGENCY_STOP")
            except Exception as e:
                results['errors'].append(f"Circuit breaker: {str(e)[:20]}")
            
            msg = f"🚨 EMERGENCY STOP EXECUTED\n"
            msg += f"Positions closed: {results['positions_closed']}\n"
            msg += f"Orders cancelled: {results['orders_cancelled']}"
            
            if results['errors']:
                msg += f"\n⚠️ Errors: {len(results['errors'])}"
            
            self.logger.warning(f"[EMERGENCY] {results}")
            
            return ActionResult(
                success=True,
                message=msg,
                data=results,
                next_view='main'
            )
        except Exception as e:
            self.logger.error(f"[EMERGENCY] Failed: {e}")
            return ActionResult(False, f"Emergency stop failed: {str(e)[:50]}", error=str(e))
    
    async def _handle_restart_bot(self, params: Dict) -> ActionResult:
        """
        Restart the bot by exiting cleanly.
        
        When run with AutoRestart mode (.\run_live.ps1 -AutoRestart),
        the script will automatically restart the bot.
        """
        import os
        import sys
        import asyncio
        
        try:
            self.logger.info("[RESTART] Bot restart requested via Telegram")
            
            # Schedule exit after response is sent
            async def do_exit():
                await asyncio.sleep(1.5)
                self.logger.info("[RESTART] Exiting for restart...")
                # Exit with code 1 to trigger AutoRestart
                os._exit(1)
            
            asyncio.create_task(do_exit())
            
            return ActionResult(
                success=True,
                message="🔄 Bot yeniden başlatılıyor...\n\n⚠️ AutoRestart modu aktif değilse manuel başlatın:\n`run_live.ps1 -AutoRestart`",
                next_view='main'
            )
        except Exception as e:
            self.logger.error(f"[RESTART] Failed: {e}")
            return ActionResult(False, f"Restart failed: {str(e)[:50]}", error=str(e))
    
    # ==================== ADVANCED SETTINGS HANDLERS ====================
    
    def _save_to_policy(self, path: str, value: Any) -> bool:
        """Save a value to policy.yaml at given path."""
        import yaml
        import os as os_module
        
        try:
            policy_path = os_module.path.join(os_module.getcwd(), 'configs', 'policy.yaml')
            
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            
            # Navigate to path and set value
            keys = path.split('.')
            current = policy_data
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = value
            
            with open(policy_path, 'w', encoding='utf-8') as f:
                yaml.dump(policy_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            self._policy = None  # Clear cache
            return True
        except Exception as e:
            self.logger.error(f"Failed to save to policy: {e}")
            return False
    
    async def _handle_set_min_size(self, params: Dict) -> ActionResult:
        """Set minimum position size percentage."""
        value = params.get('view', params.get('v', ''))
        if not value:
            return ActionResult(False, "Value required", error="MISSING_VALUE")
        
        try:
            pct = int(value) / 100  # Convert % to decimal
            if self._save_to_policy('trading.scoring.position_sizing.min_percentage', pct):
                return ActionResult(True, f"Min Size: {value}%\n\n⚠️ Restart gerektirir", next_view='adv_size')
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_set_max_size(self, params: Dict) -> ActionResult:
        """Set maximum position size percentage."""
        value = params.get('view', params.get('v', ''))
        if not value:
            return ActionResult(False, "Value required", error="MISSING_VALUE")
        
        try:
            pct = int(value) / 100
            if self._save_to_policy('trading.scoring.position_sizing.max_percentage', pct):
                return ActionResult(True, f"Max Size: {value}%\n\n⚠️ Restart gerektirir", next_view='adv_size')
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_add_coin(self, params: Dict) -> ActionResult:
        """Add a coin to trading pairs with full onboarding.
        
        Steps:
        1. Add to trading_pairs in policy.yaml
        2. Register with CoinRegistry (auto tier classification)
        3. Return tier info to user
        """
        symbol = params.get('sym', params.get('s', ''))
        if not symbol:
            return ActionResult(False, "Symbol required", error="MISSING_SYMBOL")
        
        try:
            import yaml
            import os as os_module
            from loguru import logger
            
            # Format symbol
            if not symbol.endswith('-USDT-SWAP'):
                symbol = f"{symbol.upper()}-USDT-SWAP"
            
            base = symbol.split('-')[0]
            
            # Step 1: Add to trading_pairs in policy.yaml
            policy_path = os_module.path.join(os_module.getcwd(), 'configs', 'policy.yaml')
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            
            trading_pairs = policy_data.get('exchange', {}).get('symbols', {}).get('trading_pairs', [])
            
            if symbol in trading_pairs:
                return ActionResult(False, f"{symbol} zaten mevcut", next_view='adv_coins')
            
            trading_pairs.append(symbol)
            policy_data['exchange']['symbols']['trading_pairs'] = trading_pairs
            
            with open(policy_path, 'w', encoding='utf-8') as f:
                yaml.dump(policy_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Step 2: Register with CoinRegistry (auto tier classification)
            tier = 'tier_4'  # Default
            ml_status = 'TA-only'
            try:
                from application.coin_registry import get_coin_registry
                registry = get_coin_registry()
                tier = await registry.register_coin(symbol, source='telegram')
                
                # Check ML status
                if registry.has_ml_model(symbol):
                    ml_status = 'ML active'
                else:
                    ml_status = 'TA-only'
                    
                logger.info(f"[COIN_ONBOARDING] {base} → {tier}, {ml_status}, source=telegram")
            except Exception as reg_err:
                logger.warning(f"[COIN_ONBOARDING] Registry error for {base}: {reg_err}")
            
            self._policy = None
            return ActionResult(
                True, 
                f"✅ {base} eklendi\n📊 Tier: {tier}\n🤖 {ml_status}\n\n⚠️ Restart gerektirir", 
                next_view='adv_coins'
            )
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_remove_coin(self, params: Dict) -> ActionResult:
        """Remove a coin from trading pairs."""
        symbol = params.get('sym', params.get('s', ''))
        if not symbol:
            return ActionResult(False, "Symbol required", error="MISSING_SYMBOL")
        
        try:
            import yaml
            import os as os_module
            
            policy_path = os_module.path.join(os_module.getcwd(), 'configs', 'policy.yaml')
            with open(policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            
            trading_pairs = policy_data.get('exchange', {}).get('symbols', {}).get('trading_pairs', [])
            
            if symbol not in trading_pairs:
                return ActionResult(False, f"{symbol} bulunamadı", next_view='adv_active')
            
            trading_pairs.remove(symbol)
            policy_data['exchange']['symbols']['trading_pairs'] = trading_pairs
            
            with open(policy_path, 'w', encoding='utf-8') as f:
                yaml.dump(policy_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            self._policy = None
            base = symbol.split('-')[0]
            return ActionResult(True, f"❌ {base} kaldırıldı\n\n⚠️ Restart gerektirir", next_view='adv_active')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_set_threshold(self, params: Dict) -> ActionResult:
        """Adjust a decision threshold."""
        key = params.get('k', '')
        direction = params.get('d', '')
        
        if not key or not direction:
            return ActionResult(False, "Key and direction required")
        
        try:
            policy = self._get_policy()
            thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
            current = thresholds.get(key, 50)
            
            step = 2
            if direction == 'up':
                new_val = min(80, current + step)
            else:
                new_val = max(20, current - step)
            
            if self._save_to_policy(f'trading.scoring.decision_thresholds.{key}', new_val):
                name_map = {'enter_long': 'Long Giriş', 'exit_long': 'Long Çıkış', 'enter_short': 'Short Giriş', 'exit_short': 'Short Çıkış'}
                return ActionResult(True, f"{name_map.get(key, key)}: {new_val}\n\n⚠️ Restart gerektirir", next_view='adv_thresh')
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_set_age(self, params: Dict) -> ActionResult:
        """Set max position age hours."""
        value = params.get('view', params.get('v', ''))
        if not value:
            return ActionResult(False, "Value required")
        
        try:
            hours = int(value)
            if self._save_to_policy('trading.time_exit.max_position_age_hours', hours):
                return ActionResult(True, f"Pozisyon Yaşı: {hours}h\n\n⚠️ Restart gerektirir", next_view='adv_age')
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_set_weight(self, params: Dict) -> ActionResult:
        """Adjust a score weight."""
        key = params.get('k', '')
        direction = params.get('d', '')
        
        if not key or not direction:
            return ActionResult(False, "Key and direction required")
        
        try:
            policy = self._get_policy()
            scoring = policy.get('trading', {}).get('scoring', {})
            weight_key = f'{key}_weight'
            current = scoring.get(weight_key, 0.1)
            
            step = 0.1
            if direction == 'up':
                new_val = min(1.0, round(current + step, 1))
            else:
                new_val = max(0.0, round(current - step, 1))
            
            if self._save_to_policy(f'trading.scoring.{weight_key}', new_val):
                return ActionResult(True, f"{key.upper()} Weight: {new_val:.0%}\n\n⚠️ Restart gerektirir", next_view='adv_weight')
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_set_preset(self, params: Dict) -> ActionResult:
        """Set TA/ML weights using a preset (e.g., 40/60, 50/50)."""
        ta_pct = params.get('ta', '')
        ml_pct = params.get('ml', '')
        
        if not ta_pct or not ml_pct:
            return ActionResult(False, "TA and ML values required")
        
        try:
            ta_weight = int(ta_pct) / 100  # Convert 40 -> 0.4
            ml_weight = int(ml_pct) / 100  # Convert 60 -> 0.6
            
            # Validate that TA + ML is reasonable (allow 90-110% for news/risk)
            if ta_weight + ml_weight < 0.1 or ta_weight + ml_weight > 1.0:
                return ActionResult(False, "Invalid weight combination")
            
            # Save both weights
            success1 = self._save_to_policy('trading.scoring.ta_weight', ta_weight)
            success2 = self._save_to_policy('trading.scoring.ml_weight', ml_weight)
            
            if success1 and success2:
                return ActionResult(
                    True, 
                    f"✅ TA/ML: {ta_pct}%/{ml_pct}%\n\n⚠️ Restart gerektirir", 
                    next_view='adv_weight'
                )
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_toggle_mlboost(self, params: Dict) -> ActionResult:
        """Toggle ML boost on/off."""
        try:
            value = params.get('v', '0')
            enabled = value == '1'
            
            if self._save_to_policy('trading.scoring.ml_boost.enabled', enabled):
                status = "✅ Aktif" if enabled else "❌ Kapalı"
                return ActionResult(True, f"ML Boost: {status}\n\n⚠️ Restart gerektirir", next_view='adv_mlboost')
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_set_ml_tier(self, params: Dict) -> ActionResult:
        """Set ML boost tier multiplier."""
        try:
            threshold = int(params.get('th', 65))
            multiplier = int(params.get('m', 1))
            
            # Load current tiers
            policy = self._get_policy()
            ml_boost = policy.get('trading', {}).get('scoring', {}).get('ml_boost', {})
            tiers = ml_boost.get('tiers', [])
            
            # Update or add tier
            tier_found = False
            for tier in tiers:
                if tier.get('ta_threshold') == threshold:
                    tier['multiplier'] = multiplier
                    tier_found = True
                    break
            
            if not tier_found:
                tiers.append({'ta_threshold': threshold, 'multiplier': multiplier})
            
            # Save updated tiers
            if self._save_to_policy('trading.scoring.ml_boost.tiers', tiers):
                return ActionResult(
                    True, 
                    f"✅ TA ≥ {threshold}: ML × {multiplier}\n\n⚠️ Restart gerektirir", 
                    next_view='adv_mlboost'
                )
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_clear_signal_history(self, params: Dict) -> ActionResult:
        """Clear signal history for a specific symbol."""
        try:
            from application.signal_history import clear_signals
            symbol = params.get('s', '')
            if symbol:
                count = clear_signals(symbol)
                short = symbol.replace('-USDT-SWAP', '')
                return ActionResult(True, f"🗑️ {short}: {count} sinyal temizlendi", next_view='sig_hist')
            return ActionResult(False, "Symbol belirtilmedi")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_clear_all_signals(self, params: Dict) -> ActionResult:
        """Clear all signal history."""
        try:
            from application.signal_history import clear_signals
            count = clear_signals(None)
            return ActionResult(True, f"🗑️ Tüm sinyal geçmişi temizlendi ({count} sinyal)", next_view='sig_hist')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_clear_alerts(self, params: Dict) -> ActionResult:
        """Clear all alerts."""
        try:
            from application.alert_history import clear_alerts
            count = clear_alerts()
            return ActionResult(True, f"🗑️ Tüm uyarılar temizlendi ({count} mesaj)", next_view='alerts')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    # ==================== SCORE WEIGHTS PREVIEW MODE ====================
    
    async def _handle_adjust_weight(self, params: Dict) -> ActionResult:
        """Adjust a score weight without saving (preview mode)."""
        key = params.get('k', '')  # ta, ml, news, risk
        direction = params.get('d', '')
        
        if not key or not direction:
            return ActionResult(False, "Key and direction required")
        
        try:
            policy = self._get_policy()
            scoring = policy.get('trading', {}).get('scoring', {})
            weight_key = f'{key}_weight'
            
            # Use pending value if exists, else policy value
            if key in self._pending_weights:
                current = self._pending_weights[key]
            else:
                current = scoring.get(weight_key, 0.1)
            
            step = 0.05  # 5%
            if direction == 'up':
                new_val = min(1.0, round(current + step, 2))
            else:
                new_val = max(0.0, round(current - step, 2))
            
            # Store in pending
            self._pending_weights[key] = new_val
            
            return ActionResult(True, f"{key.upper()}: {int(new_val * 100)}%", next_view='adv_weight')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_save_weights(self, params: Dict) -> ActionResult:
        """Save all pending weight changes."""
        try:
            if not self._pending_weights:
                return ActionResult(False, "Bekleyen değişiklik yok")
            
            saved = []
            for key, value in self._pending_weights.items():
                weight_key = f'{key}_weight'
                if self._save_to_policy(f'trading.scoring.{weight_key}', value):
                    saved.append(f"{key.upper()}: {int(value * 100)}%")
            
            self._pending_weights.clear()
            
            if saved:
                msg = "✅ Kaydedildi:\n" + "\n".join(saved) + "\n\n⚠️ Restart gerektirir"
                return ActionResult(True, msg, next_view='adv_weight')
            return ActionResult(False, "Kaydetme başarısız")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_cancel_weights(self, params: Dict) -> ActionResult:
        """Cancel pending weight changes."""
        try:
            self._pending_weights.clear()
            return ActionResult(True, "❌ Değişiklikler iptal edildi", next_view='adv_weight')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    # ==================== THRESHOLD PREVIEW MODE ====================
    
    async def _handle_adjust_threshold(self, params: Dict) -> ActionResult:
        """Adjust a threshold without saving (preview mode)."""
        key = params.get('k', '')  # enter_long, exit_long, enter_short, exit_short
        direction = params.get('d', '')
        
        if not key or not direction:
            return ActionResult(False, "Key and direction required")
        
        try:
            policy = self._get_policy()
            thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
            
            # Use pending value if exists, else policy value
            defaults = {'enter_long': 52, 'exit_long': 40, 'enter_short': 48, 'exit_short': 60}
            if key in self._pending_thresh:
                current = self._pending_thresh[key]
            else:
                current = thresholds.get(key, defaults.get(key, 50))
            
            step = 2
            if direction == 'up':
                new_val = min(100, current + step)
            else:
                new_val = max(0, current - step)
            
            # Store in pending
            self._pending_thresh[key] = new_val
            
            labels = {'enter_long': 'L.Giriş', 'exit_long': 'L.Çıkış', 'enter_short': 'S.Giriş', 'exit_short': 'S.Çıkış'}
            return ActionResult(True, f"{labels.get(key, key)}: {new_val}", next_view='adv_thresh')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_save_thresholds(self, params: Dict) -> ActionResult:
        """Save all pending threshold changes."""
        try:
            if not self._pending_thresh:
                return ActionResult(False, "Bekleyen değişiklik yok")
            
            saved = []
            labels = {'enter_long': 'L.Giriş', 'exit_long': 'L.Çıkış', 'enter_short': 'S.Giriş', 'exit_short': 'S.Çıkış'}
            
            for key, value in self._pending_thresh.items():
                path = f'trading.scoring.decision_thresholds.{key}'
                if self._save_to_policy(path, value):
                    saved.append(f"{labels.get(key, key)}: {value}")
            
            self._pending_thresh.clear()
            
            if saved:
                msg = "✅ Kaydedildi:\n" + "\n".join(saved) + "\n\n⚠️ Restart gerektirir"
                return ActionResult(True, msg, next_view='adv_thresh')
            return ActionResult(False, "Kaydetme başarısız")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_cancel_thresholds(self, params: Dict) -> ActionResult:
        """Cancel pending threshold changes."""
        try:
            self._pending_thresh.clear()
            return ActionResult(True, "❌ Değişiklikler iptal edildi", next_view='adv_thresh')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    # ==================== ATR TP/SL HANDLERS ====================
    
    async def _handle_set_atr(self, params: Dict) -> ActionResult:
        """Set ATR TP/SL multiplier directly (legacy instant save)."""
        key = params.get('k', '')  # 'tp' or 'sl'
        value = params.get('v', '')
        
        if not key or not value:
            return ActionResult(False, "Key and value required")
        
        try:
            val = float(value)
            policy_key = 'tp_atr_mult' if key == 'tp' else 'sl_atr_mult'
            
            if self._save_to_policy(f'trading.risk.tp_sl_atr.{policy_key}', val):
                label = "TP" if key == 'tp' else "SL"
                return ActionResult(True, f"{label} ATR: {val}×\n\n⚠️ Restart gerektirir", next_view='adv_atr')
            return ActionResult(False, "Save failed")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_adjust_atr(self, params: Dict) -> ActionResult:
        """Adjust ATR multiplier without saving (preview mode)."""
        key = params.get('k', '')  # 'tp' or 'sl'
        direction = params.get('d', '')
        
        if not key or not direction:
            return ActionResult(False, "Key and direction required")
        
        try:
            policy = self._get_policy()
            atr_config = policy.get('trading', {}).get('risk', {}).get('tp_sl_atr', {})
            policy_key = 'tp_atr_mult' if key == 'tp' else 'sl_atr_mult'
            
            # Use pending value if exists
            if key in self._pending_atr:
                current = self._pending_atr[key]
            else:
                default = 4.0 if key == 'tp' else 2.0
                current = atr_config.get(policy_key, default)
            
            step = 0.5
            if direction == 'up':
                new_val = min(10.0, round(current + step, 1))
            else:
                new_val = max(0.5, round(current - step, 1))
            
            # Store in pending
            self._pending_atr[key] = new_val
            
            label = "TP" if key == 'tp' else "SL"
            return ActionResult(True, f"{label}: {new_val}×", next_view='adv_atr')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_save_atr(self, params: Dict) -> ActionResult:
        """Save all pending ATR changes."""
        try:
            if not self._pending_atr:
                return ActionResult(False, "Bekleyen değişiklik yok")
            
            saved = []
            for key, value in self._pending_atr.items():
                policy_key = 'tp_atr_mult' if key == 'tp' else 'sl_atr_mult'
                if self._save_to_policy(f'trading.risk.tp_sl_atr.{policy_key}', value):
                    label = "TP" if key == 'tp' else "SL"
                    saved.append(f"{label}: {value}×")
            
            self._pending_atr.clear()
            
            if saved:
                msg = "✅ Kaydedildi:\n" + "\n".join(saved) + "\n\n⚠️ Restart gerektirir"
                return ActionResult(True, msg, next_view='adv_atr')
            return ActionResult(False, "Kaydetme başarısız")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_cancel_atr(self, params: Dict) -> ActionResult:
        """Cancel pending ATR changes."""
        try:
            self._pending_atr.clear()
            return ActionResult(True, "❌ Değişiklikler iptal edildi", next_view='adv_atr')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    # ==================== TIER-BASED POSITION SIZING ====================
    
    async def _handle_adjust_tier(self, params: Dict) -> ActionResult:
        """Adjust a tier position percentage without saving (preview mode)."""
        key = params.get('k', '')  # weak, medium, strong, extreme
        direction = params.get('d', '')
        
        if not key or not direction:
            return ActionResult(False, "Key and direction required")
        
        try:
            policy = self._get_policy()
            tiers = policy.get('trading', {}).get('scoring', {}).get('position_sizing', {}).get('tiers', {})
            
            # Use pending value if exists, else policy value
            if key in self._pending_tiers:
                current = self._pending_tiers[key]
            else:
                current = tiers.get(key, {}).get('position_pct', 0.02)
            
            step = 0.01  # 1%
            if direction == 'up':
                new_val = min(0.30, round(current + step, 2))  # Max 30%
            else:
                new_val = max(0.01, round(current - step, 2))  # Min 1%
            
            # Store in pending
            self._pending_tiers[key] = new_val
            
            tier_names = {'weak': '🟢 Weak', 'medium': '🟡 Medium', 'strong': '🟠 Strong', 'extreme': '🔴 Extreme'}
            return ActionResult(True, f"{tier_names.get(key, key)}: {int(new_val * 100)}%", next_view='adv_size')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_save_tiers(self, params: Dict) -> ActionResult:
        """Save all pending tier changes to policy."""
        try:
            if not self._pending_tiers:
                return ActionResult(False, "Bekleyen değişiklik yok")
            
            saved = []
            tier_names = {'weak': 'Weak', 'medium': 'Medium', 'strong': 'Strong', 'extreme': 'Extreme'}
            
            for key, value in self._pending_tiers.items():
                # Path: trading.scoring.position_sizing.tiers.{key}.position_pct
                path = f'trading.scoring.position_sizing.tiers.{key}.position_pct'
                if self._save_to_policy(path, value):
                    saved.append(f"{tier_names.get(key, key)}: {int(value * 100)}%")
            
            self._pending_tiers.clear()
            
            if saved:
                msg = "✅ Kaydedildi:\n" + "\n".join(saved) + "\n\n⚠️ Restart gerektirir"
                return ActionResult(True, msg, next_view='adv_size')
            return ActionResult(False, "Kaydetme başarısız")
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_cancel_tiers(self, params: Dict) -> ActionResult:
        """Cancel pending tier changes."""
        try:
            self._pending_tiers.clear()
            return ActionResult(True, "❌ Değişiklikler iptal edildi", next_view='adv_size')
        except Exception as e:
            return ActionResult(False, f"Error: {e}")
    
    async def _handle_toggle_trading(self, params: Dict) -> ActionResult:
        """
        Toggle trading on/off.
        
        When paused:
        - trading_analysis job will skip opening new positions
        - Existing positions will continue to be managed (trailing stop, etc.)
        """
        try:
            import json
            from pathlib import Path
            
            state_file = Path("data/runtime_state.json")
            
            # Load current state
            if state_file.exists():
                with open(state_file, 'r') as f:
                    runtime_state = json.load(f)
            else:
                runtime_state = {}
            
            # Toggle trading_paused
            current_paused = runtime_state.get('trading_paused', False)
            new_paused = not current_paused
            runtime_state['trading_paused'] = new_paused
            
            # Save state
            with open(state_file, 'w') as f:
                json.dump(runtime_state, f, indent=2)
            
            if new_paused:
                self.logger.warning("⏸️ Trading PAUSED via Telegram")
                return ActionResult(
                    True, 
                    "⏸️ Trading durduruldu!\n\nYeni pozisyon açılmayacak.\nMevcut pozisyonlar yönetilmeye devam edecek.",
                    next_view='main'
                )
            else:
                self.logger.info("▶️ Trading RESUMED via Telegram")
                return ActionResult(
                    True, 
                    "▶️ Trading başlatıldı!\n\nBot normal şekilde işlem yapabilir.",
                    next_view='main'
                )
                
        except Exception as e:
            self.logger.error(f"Failed to toggle trading: {e}")
            return ActionResult(False, f"Hata: {e}")

    # ========================= TRAILING STOP HANDLERS =========================
    
    async def _handle_trail_preset(self, params: Dict) -> ActionResult:
        """Apply a trailing stop preset (aggressive, balanced, conservative)."""
        try:
            mode = params.get('m', 'balanced')
            policy = self._get_policy()
            
            presets = policy.get('trading', {}).get('scoring', {}).get('trailing', {}).get('presets', {})
            preset = presets.get(mode)
            
            if not preset:
                return ActionResult(False, f"Preset bulunamadı: {mode}")
            
            # Store all preset values as pending
            self._pending_trail = {
                'activation_r_multiple': preset.get('activation_r_multiple', 0.3),
                'breakeven_r_multiple': preset.get('breakeven_r_multiple', 0.7),
                'tight_r_multiple': preset.get('tight_r_multiple', 1.0),
                'tight_offset': preset.get('tight_offset', 0.3),
            }
            
            preset_names = {'aggressive': '🔥 Agresif', 'balanced': '⚖️ Dengeli', 'conservative': '🛡️ Konservatif'}
            return ActionResult(
                True, 
                f"{preset_names.get(mode, mode)} preset uygulandı.\nKaydetmek için ✅ Kaydet butonuna basın.",
                next_view='adv_trail'
            )
        except Exception as e:
            self.logger.error(f"Failed to apply trail preset: {e}")
            return ActionResult(False, f"Hata: {e}")
    
    async def _handle_trail_adjust(self, params: Dict) -> ActionResult:
        """Adjust a single trailing parameter."""
        try:
            key = params.get('k', '')  # activation, breakeven, tight_r, offset
            direction = params.get('d', 'up')
            
            policy = self._get_policy()
            trailing = policy.get('trading', {}).get('scoring', {}).get('trailing', {})
            
            # Map short keys to full keys
            key_map = {
                'activation': 'activation_r_multiple',
                'breakeven': 'breakeven_r_multiple', 
                'tight_r': 'tight_r_multiple',
                'offset': 'tight_offset',
            }
            full_key = key_map.get(key, key)
            
            # Get current value (from pending or policy)
            current = self._pending_trail.get(full_key) or trailing.get(full_key, 0.5)
            
            # Adjust by 0.1
            delta = 0.1 if direction == 'up' else -0.1
            new_value = round(max(0.1, current + delta), 1)
            
            # Store in pending
            self._pending_trail[full_key] = new_value
            
            return ActionResult(
                True, 
                f"{key}: {current} → {new_value}",
                next_view='adv_trail'
            )
        except Exception as e:
            self.logger.error(f"Failed to adjust trail param: {e}")
            return ActionResult(False, f"Hata: {e}")
    
    async def _handle_save_trail(self, params: Dict) -> ActionResult:
        """Save pending trailing stop settings to policy.yaml."""
        try:
            if not self._pending_trail:
                return ActionResult(False, "Kaydedilecek değişiklik yok.")
            
            # Save each pending value
            for key, value in self._pending_trail.items():
                path = f"trading.scoring.trailing.{key}"
                await asyncio.to_thread(self._save_to_policy, path, value)
            
            saved_count = len(self._pending_trail)
            self._pending_trail.clear()
            
            return ActionResult(
                True, 
                f"✅ {saved_count} trailing ayarı kaydedildi!\nDeğişiklikler hemen aktif.",
                next_view='adv_trail'
            )
        except Exception as e:
            self.logger.error(f"Failed to save trail settings: {e}")
            return ActionResult(False, f"Kaydetme hatası: {e}")
    
    async def _handle_cancel_trail(self, params: Dict) -> ActionResult:
        """Cancel pending trailing stop changes."""
        self._pending_trail.clear()
        return ActionResult(
            True, 
            "Değişiklikler iptal edildi.",
            next_view='adv_trail'
        )


# Global instance
_action_dispatcher: Optional[ActionDispatcher] = None


def get_action_dispatcher() -> ActionDispatcher:
    """Get the global action dispatcher instance."""
    global _action_dispatcher
    if _action_dispatcher is None:
        _action_dispatcher = ActionDispatcher()
    return _action_dispatcher
