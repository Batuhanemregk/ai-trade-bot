"""
Trailing Stops Job (5m)
Handles SL/TP/trailing stop updates every 5 minutes.

Features:
- Trailing Stop: Dynamically adjusts SL as profit increases
- Break-Even: Moves SL to entry at +1R
- Partial TP: Closes portions at R-multiple levels
- Time-Based Exit: Force closes stale positions
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from loguru import logger

from .base_job import BaseJob


class Trailing5mJob(BaseJob):
    """5-minute trailing stops job for position management."""
    
    # Symbols to completely ignore (don't process at all)
    IGNORED_SYMBOLS = ['MINA', 'MINA-USDT-SWAP', 'MINA/USDT:USDT']
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.exchange_adapter = None
        self.position_monitor = None
        
        # Track executed partial TP levels per symbol
        self.partial_tp_executed: Dict[str, List[int]] = {}
        
        # Track current SL algo order IDs
        self.current_sl_orders: Dict[str, str] = {}
    
    def _is_symbol_ignored(self, symbol: str) -> bool:
        """Check if symbol should be ignored."""
        if not symbol:
            return False
        base = symbol.split('-')[0].split('/')[0].upper()
        return base == 'MINA' or symbol in self.IGNORED_SYMBOLS
        
        
    async def initialize(self):
        """Initialize trailing stops components."""
        try:
            # Initialize exchange adapter
            from adapters.exchange_okx_ccxt import OKXCCXTAdapter
            self.exchange_adapter = OKXCCXTAdapter()
            
            # Initialize position monitor with real services
            from application.position_monitor import PositionMonitor
            from application.portfolio_service import PortfolioService
            from application.risk_service import RiskService
            
            portfolio_service = PortfolioService(self.exchange_adapter)
            risk_service = RiskService(self.policy)
            
            self.position_monitor = PositionMonitor(
                portfolio_service=portfolio_service,
                risk_service=risk_service,
                exchange_adapter=self.exchange_adapter,
                config={},
                policy=self.policy
            )
            
            # Initialize notification service for Telegram alerts
            try:
                from infrastructure.notification_service import NotificationService
                self.notification_service = NotificationService()
            except Exception as e:
                logger.warning(f"⚠️ Notification service not available: {e}")
                self.notification_service = None
            
            logger.info("✅ Trailing5mJob initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Trailing5mJob: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup trailing stops resources"""
        try:
            if hasattr(self, 'exchange_adapter') and self.exchange_adapter:
                await self.exchange_adapter.close()
                logger.debug("✅ Closed exchange adapter for Trailing5mJob")
        except Exception as e:
            logger.error(f"❌ Trailing5mJob cleanup failed: {e}")
    
    def _get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value from policy."""
        trading = self.policy.get('trading', {})
        # Features are directly under trading, not trading.scoring
        return trading.get(key, {}) if default is None else trading.get(key, default)
    
    async def execute(self):
        """Execute 5-minute trailing stops update."""
        try:
            logger.info("[JOB] trailing_5m starting execution")
            
            # Get config
            trailing_config = self._get_config('trailing', {})
            partial_tp_config = self._get_config('partial_tp', {})
            time_exit_config = self._get_config('time_exit', {})
            
            # Check if any features are enabled
            trailing_enabled = trailing_config.get('enabled', False)
            partial_tp_enabled = partial_tp_config.get('enabled', False)
            time_exit_enabled = time_exit_config.get('enabled', False)
            
            if not any([trailing_enabled, partial_tp_enabled, time_exit_enabled]):
                logger.info("[TRAIL] All exit strategy features disabled in policy")
                return
            
            logger.info(f"[TRAIL] Features: trailing={trailing_enabled}, partial_tp={partial_tp_enabled}, time_exit={time_exit_enabled}")
            
            # Get all active positions
            active_positions = await self._get_active_positions()
            
            if not active_positions:
                logger.info("[TRAIL] No active positions to monitor")
                return
            
            logger.info(f"[TRAIL] Monitoring {len(active_positions)} active positions")
            
            processed_count = 0
            for symbol in active_positions:
                try:
                    # Skip ignored symbols (e.g., MINA)
                    if self._is_symbol_ignored(symbol):
                        logger.debug(f"[TRAIL] {symbol} is in ignore list, skipping")
                        continue
                    
                    # Check bar idempotency
                    if self.is_bar_already_processed(symbol, '5m'):
                        logger.debug(f"[BAR] {symbol} 5m bar already processed, skipping")
                        continue
                    
                    # Get position info
                    position = await self._get_position_info(symbol)
                    if not position:
                        continue
                    
                    # Get current price
                    current_price = await self._get_current_price(symbol)
                    if not current_price:
                        continue
                    
                    # Calculate R-multiple
                    r_multiple = self._calculate_r_multiple(position, current_price)
                    logger.info(f"[TRAIL] {symbol} R-multiple: {r_multiple:.3f}")
                    
                    # Process features in order
                    
                    # 1. Time-based exit check (highest priority - force close)
                    if time_exit_enabled:
                        closed = await self._check_time_exit(symbol, position, time_exit_config)
                        if closed:
                            processed_count += 1
                            continue  # Position closed, skip other checks
                    
                    # 2. Partial TP check
                    if partial_tp_enabled and r_multiple > 0:
                        await self._check_partial_tp(symbol, position, r_multiple, current_price, partial_tp_config)
                    
                    # 3. Trailing stop check
                    if trailing_enabled:
                        await self._process_trailing_stop(symbol, position, current_price, r_multiple, trailing_config)
                    
                    # Mark bar as processed
                    self.mark_bar_processed(symbol, '5m')
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process {symbol}: {e}")
                    continue
            
            logger.info(f"[JOB] trailing_5m completed {processed_count}/{len(active_positions)} positions")
            
        except Exception as e:
            logger.error(f"❌ Trailing5mJob execution failed: {e}")
            raise
    
    async def _get_active_positions(self) -> List[str]:
        """Get list of symbols with active positions."""
        try:
            # Use exchange adapter directly for reliability
            positions = self.exchange_adapter.ccxt_client.fetch_positions()
            active = []
            for pos in positions:
                contracts = abs(float(pos.get('contracts', 0)))
                if contracts > 0:
                    # Convert CCXT symbol to OKX format
                    symbol = pos.get('symbol', '')
                    if '/' in symbol:
                        parts = symbol.replace(':USDT', '').split('/')
                        symbol = f"{parts[0]}-USDT-SWAP"
                    active.append(symbol)
            return active
            
        except Exception as e:
            logger.error(f"❌ Failed to get active positions: {e}")
            return []
    
    async def _get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get position information for a symbol including SL."""
        try:
            positions = self.exchange_adapter.ccxt_client.fetch_positions()
            
            for pos in positions:
                pos_symbol = pos.get('symbol', '')
                # Check if symbol matches
                if symbol.split('-')[0] in pos_symbol:
                    contracts = abs(float(pos.get('contracts', 0)))
                    if contracts > 0:
                        entry_price = float(pos.get('entryPrice', 0))
                        side = pos.get('side', 'long')
                        
                        # Get position open time if available
                        timestamp = pos.get('timestamp')
                        opened_at = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc) if timestamp else None
                        
                        # Get current SL order from exchange
                        stop_loss = None
                        try:
                            sl_order = await self.exchange_adapter.get_position_sl_order(symbol)
                            if sl_order:
                                stop_loss = sl_order.get('triggerPrice')
                                logger.debug(f"[TRAIL] {symbol} SL from exchange: {stop_loss}")
                        except Exception as sl_err:
                            logger.warning(f"[TRAIL] {symbol} Could not fetch SL: {sl_err}")
                        
                        return {
                            'symbol': symbol,
                            'entry_price': entry_price,
                            'side': side,
                            'size': contracts,
                            'opened_at': opened_at,
                            'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                            'stop_loss': stop_loss
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get position info for {symbol}: {e}")
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            ticker = await self.exchange_adapter.fetch_ticker(symbol)
            return float(ticker['last'])
            
        except Exception as e:
            logger.error(f"❌ Failed to get current price for {symbol}: {e}")
            return None
    
    def _calculate_r_multiple(self, position: Dict[str, Any], current_price: float) -> float:
        """
        Calculate TRUE R-multiple for a position.
        
        R-multiple = PnL / Risk, where:
        - PnL = current price distance from entry
        - Risk = distance from entry to stop loss (1R)
        
        Example: Entry=100, SL=98, Current=101
        - Risk = 100 - 98 = 2
        - PnL = 101 - 100 = 1  
        - R = 1 / 2 = 0.5R
        """
        try:
            entry_price = position['entry_price']
            stop_loss = position.get('stop_loss')
            side = position['side']
            
            # If no SL available, cannot calculate true R-multiple
            if stop_loss is None:
                logger.warning(f"[TRAIL] {position.get('symbol')} No SL available, using percentage-based R")
                # Fallback to percentage (but log warning)
                if side == 'long':
                    return (current_price - entry_price) / entry_price
                else:
                    return (entry_price - current_price) / entry_price
            
            # Calculate risk (1R = distance to SL)
            risk = abs(entry_price - stop_loss)
            if risk == 0:
                logger.warning(f"[TRAIL] {position.get('symbol')} Risk is 0 (SL = entry)")
                return 0.0
            
            # Calculate PnL
            if side == 'long':
                pnl = current_price - entry_price
            else:
                pnl = entry_price - current_price
            
            r_multiple = pnl / risk
            
            logger.debug(f"[TRAIL] {position.get('symbol')} R-calc: entry={entry_price}, SL={stop_loss}, "
                        f"current={current_price}, risk={risk:.4f}, pnl={pnl:.4f}, R={r_multiple:.3f}")
            
            return r_multiple
                
        except Exception as e:
            logger.error(f"❌ Failed to calculate R-multiple: {e}")
            return 0.0
    
    # ============================================================
    # TRAILING STOP IMPLEMENTATION
    # ============================================================
    
    async def _process_trailing_stop(self, symbol: str, position: Dict[str, Any], 
                                     current_price: float, r_multiple: float,
                                     config: Dict[str, Any]):
        """Process trailing stop for a position with real OKX sync."""
        try:
            activation_r = config.get('activation_r_multiple', 0.5)
            breakeven_r = config.get('breakeven_r_multiple', 1.0)
            tight_r = config.get('tight_r_multiple', 1.5)
            tight_offset = config.get('tight_offset', 0.3)
            
            side = position['side']
            entry_price = position['entry_price']
            
            # Check if trailing should be activated
            if r_multiple < activation_r:
                logger.debug(f"[TRAIL] {symbol} R={r_multiple:.3f} < {activation_r}, not activated")
                return
            
            # Calculate new stop price based on R-multiple
            if r_multiple >= tight_r:
                # Tight trailing stop
                offset = tight_offset / 100  # Convert to decimal
                if side == 'long':
                    new_stop = current_price * (1 - offset)
                else:
                    new_stop = current_price * (1 + offset)
                logger.info(f"[TRAIL] {symbol} TIGHT trailing @ R={r_multiple:.2f}: new_stop={new_stop:.4f}")
                
            elif r_multiple >= breakeven_r:
                # Breakeven + small buffer
                buffer = 0.001  # 0.1% buffer
                if side == 'long':
                    new_stop = entry_price * (1 + buffer)
                else:
                    new_stop = entry_price * (1 - buffer)
                logger.info(f"[TRAIL] {symbol} BREAKEVEN @ R={r_multiple:.2f}: new_stop={new_stop:.4f} (entry={entry_price:.4f})")
                
            else:
                # Normal trailing (0.5R - 1R)
                trail_pct = 0.02  # 2% trail
                if side == 'long':
                    new_stop = current_price * (1 - trail_pct)
                else:
                    new_stop = current_price * (1 + trail_pct)
                logger.info(f"[TRAIL] {symbol} NORMAL trailing @ R={r_multiple:.2f}: new_stop={new_stop:.4f}")
            
            # Get current SL order from OKX
            current_sl = await self.exchange_adapter.get_position_sl_order(symbol)
            current_algo_id = current_sl.get('algoId') if current_sl else self.current_sl_orders.get(symbol)
            
            # Check if new stop is better than current
            should_update = True
            if current_sl:
                current_stop = current_sl.get('triggerPrice', 0)
                if side == 'long':
                    # For long: new stop should be higher (move up)
                    should_update = new_stop > current_stop
                else:
                    # For short: new stop should be lower (move down)
                    should_update = new_stop < current_stop
                
                if not should_update:
                    logger.debug(f"[TRAIL] {symbol} new_stop={new_stop:.4f} not better than current={current_stop:.4f}")
                    return
            
            # Update stop loss on OKX
            result = await self.exchange_adapter.update_stop_loss(
                symbol=symbol,
                new_stop_price=new_stop,
                position_size=position['size'],
                side=side,
                current_algo_id=current_algo_id
            )
            
            if result.get('success'):
                self.current_sl_orders[symbol] = result.get('algoId')
                logger.info(f"✅ [TRAIL] {symbol} SL synced to OKX: {new_stop:.4f}")
                
                # Send Telegram notification
                if self.notification_service:
                    is_tight = r_multiple >= tight_r
                    is_breakeven = r_multiple >= breakeven_r
                    short_sym = symbol.replace('-USDT-SWAP', '')
                    await self.notification_service.send_trailing_notification(
                        symbol=short_sym,
                        be_price=new_stop,
                        tightened=is_tight
                    )
            else:
                logger.warning(f"⚠️ [TRAIL] {symbol} Failed to sync SL: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to process trailing stop for {symbol}: {e}")
    
    # ============================================================
    # PARTIAL TAKE PROFIT IMPLEMENTATION
    # ============================================================
    
    async def _check_partial_tp(self, symbol: str, position: Dict[str, Any],
                                r_multiple: float, current_price: float,
                                config: Dict[str, Any]):
        """Check and execute partial take profit levels."""
        try:
            levels = config.get('levels', [])
            if not levels:
                return
            
            # Get already executed levels for this symbol
            executed = self.partial_tp_executed.get(symbol, [])
            
            for i, level in enumerate(levels):
                level_r = level.get('r_multiple', 0)
                close_pct = level.get('close_pct', 0)
                
                # Skip already executed levels
                if i in executed:
                    continue
                
                # Check if R-multiple reached this level
                if r_multiple >= level_r:
                    # Calculate size to close
                    close_size = position['size'] * close_pct
                    
                    logger.info(f"💰 [PARTIAL_TP] {symbol} Level {i+1} reached @ R={level_r}: closing {close_pct*100:.0f}% ({close_size:.4f})")
                    
                    # Execute partial close
                    result = await self.exchange_adapter.close_position_market(
                        symbol=symbol,
                        size=close_size,
                        side=position['side'],
                        reason=f"Partial TP Level {i+1} @ {level_r}R"
                    )
                    
                    if result.get('id'):
                        # Mark level as executed
                        if symbol not in self.partial_tp_executed:
                            self.partial_tp_executed[symbol] = []
                        self.partial_tp_executed[symbol].append(i)
                        
                        logger.info(f"✅ [PARTIAL_TP] {symbol} Level {i+1} executed: {close_size:.4f} closed")
                        
                        # Send Telegram notification
                        if self.notification_service:
                            short_sym = symbol.replace('-USDT-SWAP', '')
                            remaining = position['size'] - close_size
                            pnl_estimate = close_size * current_price * (level_r * 0.02)  # Approximate
                            await self.notification_service.send_exit_notification(
                                symbol=short_sym,
                                reason=f"Partial TP Lvl{i+1} ({close_pct*100:.0f}% @ {level_r}R)",
                                pnl=pnl_estimate,
                                r_multiple=r_multiple
                            )
                    else:
                        logger.warning(f"⚠️ [PARTIAL_TP] {symbol} Level {i+1} failed: {result.get('error')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to check partial TP for {symbol}: {e}")
    
    # ============================================================
    # TIME-BASED EXIT IMPLEMENTATION
    # ============================================================
    
    async def _check_time_exit(self, symbol: str, position: Dict[str, Any],
                               config: Dict[str, Any]) -> bool:
        """Check if position should be force-closed due to age."""
        try:
            max_age_hours = config.get('max_position_age_hours', 24)
            warning_hours = config.get('warning_hours', 20)
            action = config.get('stale_position_action', 'close')
            
            opened_at = position.get('opened_at')
            if not opened_at:
                # Can't determine age, skip
                return False
            
            now = datetime.now(timezone.utc)
            age = now - opened_at
            age_hours = age.total_seconds() / 3600
            
            logger.debug(f"[TIME_EXIT] {symbol} age={age_hours:.1f}h max={max_age_hours}h")
            
            # Check warning threshold
            if age_hours >= warning_hours and age_hours < max_age_hours:
                remaining = max_age_hours - age_hours
                logger.warning(f"⏰ [TIME_EXIT] {symbol} WARNING: Position {age_hours:.1f}h old, {remaining:.1f}h until force close")
            
            # Check max age
            if age_hours >= max_age_hours:
                logger.warning(f"⏰ [TIME_EXIT] {symbol} MAX AGE REACHED ({age_hours:.1f}h >= {max_age_hours}h)")
                
                if action == 'close':
                    # Force close the position
                    result = await self.exchange_adapter.close_position_market(
                        symbol=symbol,
                        size=position['size'],
                        side=position['side'],
                        reason=f"Time-based exit ({age_hours:.1f}h)"
                    )
                    
                    if result.get('id'):
                        logger.info(f"✅ [TIME_EXIT] {symbol} Force closed after {age_hours:.1f}h")
                        
                        # Send Telegram notification
                        if self.notification_service:
                            short_sym = symbol.replace('-USDT-SWAP', '')
                            await self.notification_service.send_exit_notification(
                                symbol=short_sym,
                                reason=f"Time Exit ({age_hours:.1f}h)",
                                pnl=0,  # PnL unknown at this point
                                r_multiple=0
                            )
                        
                        # Clean up tracking
                        if symbol in self.partial_tp_executed:
                            del self.partial_tp_executed[symbol]
                        if symbol in self.current_sl_orders:
                            del self.current_sl_orders[symbol]
                        
                        return True
                    else:
                        logger.error(f"❌ [TIME_EXIT] {symbol} Failed to close: {result.get('error')}")
                
                elif action == 'alert':
                    logger.warning(f"🔔 [TIME_EXIT] {symbol} ALERT: Position {age_hours:.1f}h old (action=alert)")
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Failed to check time exit for {symbol}: {e}")
            return False
    
    def _is_stop_hit(self, side: str, current_price: float, stop_price: float) -> bool:
        """Check if trailing stop is hit."""
        if side == 'long':
            return current_price <= stop_price
        else:
            return current_price >= stop_price
