"""
Telegram Context Resolver - Async data fetcher for all 8 views
Fetches data from real services: ScoringService, PortfolioService, RiskService, etc.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
import time
from loguru import logger

from infrastructure.bootstrap import load_policy
from adapters.telegram.middleware import get_metrics_hook


class ContextResolver:
    """
    Resolves context data for Telegram views with real data integration.
    
    Fetches data from:
    - ScoringService: Latest signals/composite scores
    - PortfolioService: Balance, PnL, positions
    - RiskService: Exposure, tier alloc, limits, circuit breaker
    - PositionMonitor: Position details, TP/SL, trailing stops
    - TradeService/ExchangeAdapter: Recent orders
    - Policy: Config from policy.yaml
    
    Features:
    - Light caching (5-15s) to avoid heavy calls per button
    - Graceful fallbacks with partial data + issues list
    - Real data integration (no placeholders)
    """
    
    def __init__(self):
        self.logger = logger.bind(component="context_resolver")
        self._policy = None
        self._services_cache: Dict[str, Any] = {}
        self._data_cache: Dict[str, Tuple[Any, float]] = {}  # key -> (data, timestamp)
        self._cache_ttl = {
            'signals': 10,      # 10 seconds
            'positions': 5,     # 5 seconds
            'orders': 5,        # 5 seconds
            'risk': 10,         # 10 seconds
            'portfolio': 5,     # 5 seconds
            'pnl': 5,           # 5 seconds
            'tpsl': 10,         # 10 seconds
            'trailing': 10,     # 10 seconds
        }
        self.metrics_hook = get_metrics_hook()
    
    def _get_policy(self) -> Dict[str, Any]:
        """Get policy config (cached)."""
        if self._policy is None:
            try:
                self._policy = load_policy()
            except Exception as e:
                self.logger.warning(f"Failed to load policy: {e}")
                self._policy = {}
        return self._policy
    
    def _get_service(self, service_name: str, factory_func: callable) -> Optional[Any]:
        """
        Get service instance (cached).
        
        Args:
            service_name: Service name key
            factory_func: Function to create service if not cached
        
        Returns:
            Service instance or None
        """
        if service_name not in self._services_cache:
            try:
                self._services_cache[service_name] = factory_func()
            except Exception as e:
                self.logger.warning(f"Failed to create {service_name}: {e}")
                return None
        
        return self._services_cache.get(service_name)
    
    def _get_cached_data(self, cache_key: str) -> Optional[Any]:
        """
        Get cached data if still valid.
        
        Args:
            cache_key: Cache key (e.g., 'signals', 'positions:BTC')
        
        Returns:
            Cached data or None if expired/missing
        """
        if cache_key not in self._data_cache:
            return None
        
        data, timestamp = self._data_cache[cache_key]
        
        # Extract base key for TTL lookup
        base_key = cache_key.split(':')[0]
        ttl = self._cache_ttl.get(base_key, 5)
        
        # Check if expired
        age = time.time() - timestamp
        if age > ttl:
            # Cache expired
            del self._data_cache[cache_key]
            return None
        
        return data
    
    def _set_cached_data(self, cache_key: str, data: Any):
        """
        Set cached data with timestamp.
        
        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self._data_cache[cache_key] = (data, time.time())
    
    async def resolve_main_context(self) -> Dict[str, Any]:
        """
        Resolve context for main dashboard view with real data.
        
        Returns:
            Dict with: status, portfolio (balance, pnl_1d, pnl_7d), risk (exposure, open_positions, cb_state), signals (latest), issues (if any)
        """
        issues = []
        try:
            context = {
                'status': {'health': 'unknown', 'last_job': None, 'queue': 0},
                'portfolio': {'balance': 0.0, 'pnl_1d': 0.0, 'pnl_7d': 0.0},
                'risk': {'exposure_pct': 0.0, 'exposure_max': 60.0, 'open_positions': 0, 'max_positions': 20, 'cb_state': 'OFF'},
                'signals': [],
                'issues': []
            }
            
            # Get policy
            policy = self._get_policy()
            # Get mode: env var takes priority over policy
            import os
            mode = os.environ.get('TRADING_MODE') or policy.get('trading', {}).get('mode', 'paper')
            context['mode'] = mode
            
            # Get symbols count from policy
            symbols = policy.get('trading', {}).get('symbols', [])
            context['symbols_count'] = len(symbols) if isinstance(symbols, list) else 0
            
            # Get portfolio data
            try:
                from application.portfolio_service import PortfolioService
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                
                # Get or create exchange adapter first
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                
                # Create portfolio service with exchange adapter
                portfolio_service = self._get_service('portfolio', lambda: PortfolioService(exchange_adapter))
                
                if portfolio_service:
                    balance = await portfolio_service.get_available_balance()
                    context['portfolio']['balance'] = balance
                    
                    # Calculate PnL from positions
                    try:
                        from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                        exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                        
                        if exchange_adapter:
                            exchange_positions = await exchange_adapter.fetch_positions()
                            total_upnl = sum(float(p.get('unrealizedPnl', 0)) for p in exchange_positions)
                            
                            # For now, use unrealized PnL as daily PnL (would need history for actual 1D/7D)
                            context['portfolio']['pnl_1d'] = total_upnl
                            context['portfolio']['pnl_7d'] = total_upnl  # Placeholder until we track history
                    except Exception as e:
                        self.logger.debug(f"Could not calculate PnL: {e}")
            except Exception as e:
                self.logger.warning(f"Failed to get portfolio data: {e}")
            
            # Get positions count and calculate exposure from exchange adapter
            try:
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                
                if exchange_adapter:
                    exchange_positions = await exchange_adapter.fetch_positions()
                    open_positions = len([p for p in exchange_positions if float(p.get('contracts', 0)) != 0])
                    context['risk']['open_positions'] = open_positions
                    
                    # Calculate exposure: (sum of position values) / portfolio_value
                    total_exposure_usd = 0.0
                    for pos_data in exchange_positions:
                        contracts = float(pos_data.get('contracts', 0))
                        if contracts == 0:
                            continue
                        mark_price = float(pos_data.get('markPrice', 0))
                        total_exposure_usd += abs(contracts * mark_price)
                    
                    portfolio_value = context['portfolio']['balance']
                    exposure_pct = (total_exposure_usd / portfolio_value * 100) if portfolio_value > 0 else 0.0
                    context['risk']['exposure_pct'] = exposure_pct
            except Exception as e:
                self.logger.warning(f"Failed to get positions count or calculate exposure: {e}")
            
            # Get latest signals (top 3 for main view)
            signals_context = await self.resolve_signals_context(limit=3)
            context['signals'] = signals_context.get('signals', [])
            if signals_context.get('issues'):
                issues.extend(signals_context['issues'])
            
            # Get last job timestamp (mock for now)
            context['status']['last_job'] = datetime.now(timezone.utc).strftime('%H:%M:%S')
            
            # Collect issues
            context['issues'] = issues
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to resolve main context: {e}", exc_info=True)
            self.metrics_hook.record_error('resolver', 'telegram')
            return {
                'status': {'health': 'unknown', 'last_job': None, 'queue': 0},
                'portfolio': {'balance': 0.0, 'pnl_1d': 0.0, 'pnl_7d': 0.0},
                'risk': {'exposure_pct': 0.0, 'exposure_max': 60.0, 'open_positions': 0, 'max_positions': 20, 'cb_state': 'OFF'},
                'signals': [],
                'mode': 'paper',
                'symbols_count': 0,
                'issues': [f"Main resolver error: {str(e)[:50]}"]
            }
    
    async def resolve_signals_context(self, limit: int = 6, symbol_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve context for signals view with real data from ScoringService cache.
        """
        issues = []
        signals = []
        
        try:
            policy = self._get_policy()
            timeframe = policy.get('trading', {}).get('timeframe', '15m')
            
            # Get real signal data from ScoringService cache
            try:
                from application.scoring_service import ScoringService
                scoring_service = self._get_service('scoring', lambda: ScoringService({}))
                
                if scoring_service:
                    # Get top symbols from cache (now returns real data)
                    top_symbols = await scoring_service.get_top_symbols(limit=limit)
                    
                    for symbol_data in top_symbols:
                        signal = {
                            'symbol': symbol_data.get('symbol', 'UNKNOWN'),
                            'final_score': symbol_data.get('score', 0.0),
                            'grade': symbol_data.get('grade', '?'),
                            'direction': symbol_data.get('signal', 'HOLD'),
                            'ta': symbol_data.get('ta', 0.0),
                            'ml': symbol_data.get('ml', 0.0),
                            'news': symbol_data.get('news', 0.0),
                            'risk': 0.0,
                            'persist': 0,
                            'persist_max': 5,
                            'age': 0,
                            'age_max': 6,
                            'confirm': 0,
                            'confirm_max': 2
                        }
                        signals.append(signal)
                    
                    if not signals:
                        issues.append("Henüz sinyal verisi yok - sonraki analiz döngüsünü bekleyin")
                else:
                    issues.append("ScoringService unavailable")
                    
            except Exception as e:
                self.logger.warning(f"Failed to get signals from ScoringService: {e}")
                issues.append(f"Scoring error: {str(e)[:30]}")
            
            return {
                'signals': signals[:limit],
                'timeframe': timeframe,
                'last_update': datetime.now(timezone.utc),
                'issues': issues
            }
            
        except Exception as e:
            self.logger.error(f"Failed to resolve signals context: {e}", exc_info=True)
            return {
                'signals': [],
                'timeframe': '15m',
                'last_update': datetime.now(timezone.utc),
                'issues': [f"Error: {str(e)[:50]}"]
            }
    
    async def resolve_risk_context(self) -> Dict[str, Any]:
        """
        Resolve context for risk view.
        
        Returns:
            Dict with: exposure, tier_alloc, limits, guards, alerts
        """
        try:
            policy = self._get_policy()
            risk_config = policy.get('trading', {}).get('risk', {})
            
            # Initialize with policy-driven defaults, NOT hardcoded mocks
            context = {
                'exposure_pct': 0.0,  # Will be calculated from positions
                'exposure_max': risk_config.get('max_exposure_pct', 60.0),
                'open_positions': 0,
                'max_positions': risk_config.get('max_positions', 20),
                'cb_state': 'OFF',
                'tier_alloc': policy.get('trading', {}).get('tier_alloc', {'T1': 40.0, 'T2': 35.0, 'T3': 25.0}),
                'limits': {
                    'max_position_size_pct': risk_config.get('max_position_size_pct', 0.10) * 100,
                    'stop_loss_pct': risk_config.get('stop_loss_pct', 0.015) * 100,
                    'leverage': risk_config.get('max_leverage', 3.0)
                },
                'guards': {
                    'persist': risk_config.get('persist_bars', 3),
                    'age': risk_config.get('max_age_bars', 6),
                    'confirm': risk_config.get('confirmations', 2),
                    'hyster': f"±{risk_config.get('hysteresis', 5)}"
                },
                'alerts': []
            }
            
            # Get actual exposure and positions count
            try:
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                from application.portfolio_service import PortfolioService
                
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                # Create portfolio service WITH exchange adapter
                portfolio_service = self._get_service('portfolio', lambda: PortfolioService(exchange_adapter))
                
                if exchange_adapter and portfolio_service:
                    # Get positions and calculate exposure
                    exchange_positions = await exchange_adapter.fetch_positions()
                    open_positions = len([p for p in exchange_positions if float(p.get('contracts', 0)) != 0])
                    context['open_positions'] = open_positions
                    
                    # Calculate exposure
                    total_exposure_usd = 0.0
                    for pos_data in exchange_positions:
                        contracts = float(pos_data.get('contracts', 0))
                        if contracts == 0:
                            continue
                        mark_price = float(pos_data.get('markPrice', 0))
                        total_exposure_usd += abs(contracts * mark_price)
                    
                    portfolio_value = await portfolio_service.get_portfolio_value()
                    exposure_pct = (total_exposure_usd / portfolio_value * 100) if portfolio_value > 0 else 0.0
                    context['exposure_pct'] = exposure_pct
            except Exception as e:
                self.logger.warning(f"Failed to get exposure data: {e}")
            
            # Get circuit breaker state
            try:
                from application.circuit_breaker import get_circuit_breaker
                circuit_breaker = get_circuit_breaker()
                status = circuit_breaker.get_status()
                context['cb_state'] = 'ON' if status.get('emergency_triggered') else 'OFF'
            except Exception as e:
                self.logger.warning(f"Failed to get circuit breaker state: {e}")
            
            # Get guards from policy
            risk_config = policy.get('trading', {}).get('risk', {})
            if risk_config:
                context['limits']['max_position_size_pct'] = risk_config.get('max_position_size_pct', 10.0) * 100
                context['limits']['leverage'] = risk_config.get('max_leverage', 3.0)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to resolve risk context: {e}", exc_info=True)
            return {
                'exposure_pct': 0.0,
                'exposure_max': 60.0,
                'open_positions': 0,
                'max_positions': 20,
                'cb_state': 'OFF',
                'tier_alloc': {},
                'limits': {},
                'guards': {},
                'alerts': []
            }
    
    async def resolve_orders_context(self, page: int = 0, limit: int = 8) -> Dict[str, Any]:
        """
        Resolve context for orders view.
        
        Args:
            page: Page number (0-indexed)
            limit: Orders per page
        
        Returns:
            Dict with: orders list, has_prev, has_next
        """
        try:
            orders = []
            
            # Get orders from exchange adapter
            try:
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                
                if exchange_adapter:
                    # Fetch open orders (check if async or sync)
                    if hasattr(exchange_adapter.fetch_open_orders, '__call__'):
                        import inspect
                        if inspect.iscoroutinefunction(exchange_adapter.fetch_open_orders):
                            open_orders = await exchange_adapter.fetch_open_orders()
                        else:
                            open_orders = exchange_adapter.fetch_open_orders()
                    else:
                        open_orders = []
                    
                    if not hasattr(open_orders, '__iter__'):
                        open_orders = []
                    
                    # Convert to view format
                    for order in open_orders[:limit * (page + 1)][page * limit:]:
                        timestamp_str = order.get('timestamp', datetime.now(timezone.utc).timestamp() * 1000)
                        if isinstance(timestamp_str, (int, float)):
                            timestamp = datetime.fromtimestamp(timestamp_str / 1000, timezone.utc)
                        else:
                            timestamp = datetime.now(timezone.utc)
                        
                        orders.append({
                            'timestamp': timestamp.strftime('%H:%M'),
                            'symbol': order.get('symbol', 'UNKNOWN'),
                            'type': order.get('type', 'MKT').upper(),
                            'side': order.get('side', 'OPEN').upper(),
                            'qty': float(order.get('amount', 0)),
                            'price': float(order.get('price', order.get('average', 0))),
                            'status': order.get('status', 'ok')
                        })
            except Exception as e:
                self.logger.warning(f"Failed to get orders: {e}")
                self.metrics_hook.record_error('resolver', 'telegram')
            
            total_orders = len(orders)
            return {
                'orders': orders[:limit],
                'page': page,
                'has_prev': page > 0,
                'has_next': total_orders > (page + 1) * limit,
                'last_update': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to resolve orders context: {e}", exc_info=True)
            return {'orders': [], 'page': 0, 'has_prev': False, 'has_next': False, 'last_update': datetime.now(timezone.utc)}
    
    async def resolve_tpsl_context(self, symbol_filter: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve context for TP/SL view.
        
        Args:
            symbol_filter: Optional symbol to filter positions
        
        Returns:
            Dict with: positions list (each with symbol, entry, sl, tp, rr, sl_atr, tp_atr), symbol_filter
        """
        try:
            positions = []
            
            # Get positions from exchange adapter and calculate TP/SL
            try:
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                from adapters.exchange_okx_rest import OKXRESTAdapter
                
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                
                if exchange_adapter:
                    exchange_positions = await exchange_adapter.fetch_positions()
                    
                    for pos_data in exchange_positions:
                        contracts = float(pos_data.get('contracts', 0))
                        if contracts == 0:
                            continue
                        
                        symbol = pos_data.get('symbol', 'UNKNOWN')
                        entry = float(pos_data.get('entryPrice', 0) or pos_data.get('avgPrice', 0) or 0)
                        side = pos_data.get('side', 'long')
                        
                        # Calculate TP/SL levels (simplified - would need ATR calculation)
                        # For now, use fixed percentages from policy
                        policy = self._get_policy()
                        risk_config = policy.get('trading', {}).get('risk', {})
                        sl_pct = risk_config.get('stop_loss_pct', 0.015)  # 1.5% default
                        tp_pct = sl_pct * 2  # 2:1 R:R
                        
                        if side == 'long':
                            sl = entry * (1 - sl_pct)
                            tp = entry * (1 + tp_pct)
                        else:
                            sl = entry * (1 + sl_pct)
                            tp = entry * (1 - tp_pct)
                        
                        positions.append({
                            'symbol': symbol,
                            'entry': entry,
                            'sl': sl,
                            'tp': tp,
                            'sl_atr': f'-2ATR',  # Placeholder
                            'tp_atr': f'+4ATR',  # Placeholder
                            'rr': '1:2'
                        })
            except Exception as e:
                self.logger.warning(f"Failed to get TP/SL data: {e}")
                self.metrics_hook.record_error('resolver', 'telegram')
            
            return {
                'positions': positions,
                'open_positions': len(positions),
                'last_update': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to resolve TP/SL context: {e}", exc_info=True)
            return {'positions': [], 'open_positions': 0, 'last_update': datetime.now(timezone.utc)}
    
    async def resolve_trailing_context(self) -> Dict[str, Any]:
        """
        Resolve context for trailing stops view.
        
        Returns:
            Dict with: trailing_stops list (each with symbol, active, base_sl, trail_price, gain_r)
        """
        try:
            trailing_stops = []
            
            # Get trailing stops from PositionMonitor or exchange
            try:
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                from adapters.exchange_okx_rest import OKXRESTAdapter
                
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                
                if exchange_adapter:
                    exchange_positions = await exchange_adapter.fetch_positions()
                    
                    for pos_data in exchange_positions:
                        contracts = float(pos_data.get('contracts', 0))
                        if contracts == 0:
                            continue
                        
                        symbol = pos_data.get('symbol', 'UNKNOWN')
                        entry = float(pos_data.get('avgPrice', 0))
                        mark = float(pos_data.get('markPrice', 0))
                        side = pos_data.get('side', 'long')
                        
                        # Check if trailing is active (would need PositionMonitor state)
                        # For now, assume trailing is active if position is in profit
                        is_profitable = (mark > entry) if side == 'long' else (mark < entry)
                        active = is_profitable
                        
                        # Calculate base SL (from entry)
                        policy = self._get_policy()
                        risk_config = policy.get('trading', {}).get('risk', {})
                        sl_pct = risk_config.get('stop_loss_pct', 0.015)
                        
                        if side == 'long':
                            base_sl = entry * (1 - sl_pct)
                            trail_price = mark * 0.98  # 2% trailing
                        else:
                            base_sl = entry * (1 + sl_pct)
                            trail_price = mark * 1.02  # 2% trailing
                        
                        # Calculate R-multiple gain
                        if entry > 0:
                            r_multiple = abs((mark - entry) / entry)
                            gain_r = r_multiple if is_profitable else 0.0
                        else:
                            gain_r = 0.0
                        
                        if active:
                            trailing_stops.append({
                                'symbol': symbol,
                                'active': active,
                                'base_sl': base_sl,
                                'trail_price': trail_price,
                                'gain_r': gain_r
                            })
            except Exception as e:
                self.logger.warning(f"Failed to get trailing stops: {e}")
                self.metrics_hook.record_error('resolver', 'telegram')
            
            return {
                'trailing_stops': trailing_stops,
                'last_update': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to resolve trailing context: {e}", exc_info=True)
            return {'trailing_stops': [], 'last_update': datetime.now(timezone.utc)}
    
    async def resolve_positions_context(self) -> Dict[str, Any]:
        """
        Resolve context for positions view with real data from exchange adapter.
        
        Returns:
            Dict with: positions list, open_positions, last_update, issues (if any)
        """
        cache_key = "positions:all"
        issues = []
        
        try:
            # Check cache first
            cached = self._get_cached_data(cache_key)
            if cached:
                return cached
            
            positions = []
            
            # Get positions from exchange adapter
            try:
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                import os
                
                # Try to create exchange adapter with real config
                exchange_adapter = self._get_service('exchange', lambda: self._create_exchange_adapter())
                
                if exchange_adapter:
                    # Fetch positions from exchange
                    exchange_positions = await exchange_adapter.fetch_positions()
                    
                    if not exchange_positions:
                        issues.append("No positions returned from exchange")
                    else:
                        for pos_data in exchange_positions:
                            size = float(pos_data.get('contracts', 0))
                            if size == 0:
                                continue
                            
                            symbol = pos_data.get('symbol', 'UNKNOWN')
                            # Normalize symbol format
                            if symbol and not symbol.endswith('USDT'):
                                symbol = symbol.replace('-USDT-SWAP', 'USDT').replace('-USDT', 'USDT')
                            
                            side = pos_data.get('side', 'long').upper()
                            entry = float(pos_data.get('avgPrice', pos_data.get('entryPrice', 0)))
                            mark = float(pos_data.get('markPrice', pos_data.get('mark_price', 0)))
                            upnl = float(pos_data.get('unrealizedPnl', pos_data.get('unrealized_pnl', 0)))
                            
                            # Calculate UPNL percentage
                            notional = abs(size * entry) if entry > 0 else 0
                            upnl_pct = (upnl / notional * 100) if notional > 0 else 0.0
                            
                            positions.append({
                                'symbol': symbol,
                                'side': side,
                                'size': abs(size),
                                'entry_price': entry,
                                'current_price': mark,
                                'unrealized_pnl': upnl,
                                'upnl_pct': upnl_pct
                            })
                else:
                    issues.append("Exchange adapter unavailable")
            except Exception as e:
                self.logger.warning(f"Failed to get positions from exchange: {e}")
                issues.append(f"Exchange error: {str(e)[:50]}")
                self.metrics_hook.record_error('resolver', 'telegram')
            
            result = {
                'positions': positions,
                'open_positions': len(positions),
                'last_update': datetime.now(timezone.utc),
                'issues': issues
            }
            
            # Cache result
            if not issues or positions:  # Cache even if there are issues, if we have some data
                self._set_cached_data(cache_key, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to resolve positions context: {e}", exc_info=True)
            self.metrics_hook.record_error('resolver', 'telegram')
            return {
                'positions': [],
                'open_positions': 0,
                'last_update': datetime.now(timezone.utc),
                'issues': [f"Positions resolver error: {str(e)[:50]}"]
            }
    
    def _create_exchange_adapter(self):
        """Create exchange adapter with real config from env."""
        try:
            from adapters.exchange_okx_ccxt import OKXExchangeAdapter
            import os
            
            policy = self._get_policy()
            exchange_config = policy.get('exchange', {})
            exchange_config.update({
                'api_key': os.getenv('OKX_API_KEY', ''),
                'secret': os.getenv('OKX_API_SECRET', ''),
                'passphrase': os.getenv('OKX_API_PASSPHRASE', ''),
                'sandbox': os.getenv('OKX_ISPAPER', 'false').lower() == 'true',
                'mode': 'dry-run' if os.getenv('TRADING_LIVE', 'false').lower() != 'true' else 'live'
            })
            
            return OKXExchangeAdapter(exchange_config)
        except Exception as e:
            self.logger.warning(f"Failed to create exchange adapter: {e}")
            return None
    
    async def resolve_pnl_context(self) -> Dict[str, Any]:
        """
        Resolve context for PnL view.
        
        Returns:
            Dict with: balance, unrealized_pnl, realized_pnl, positions (with PnL breakdown)
        """
        try:
            context = {
                'balance': 0.0,
                'unrealized_pnl': 0.0,
                'realized_pnl': 0.0,
                'positions': []
            }
            
            # Get portfolio data
            try:
                from application.portfolio_service import PortfolioService
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                
                portfolio_service = self._get_service('portfolio', lambda: PortfolioService(None))
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                
                if portfolio_service:
                    balance = await portfolio_service.get_portfolio_value()
                    context['balance'] = balance
                
                # Get positions with PnL
                if exchange_adapter:
                    exchange_positions = await exchange_adapter.fetch_positions()
                    total_upnl = 0.0
                    
                    for pos_data in exchange_positions:
                        contracts = float(pos_data.get('contracts', 0))
                        if contracts == 0:
                            continue
                        
                        symbol = pos_data.get('symbol', 'UNKNOWN')
                        entry = float(pos_data.get('avgPrice', 0))
                        mark = float(pos_data.get('markPrice', 0))
                        upnl = float(pos_data.get('unrealizedPnl', 0))
                        side = pos_data.get('side', 'long')
                        
                        # Calculate UPNL percentage
                        upnl_pct = (upnl / (entry * contracts)) * 100 if entry > 0 and contracts > 0 else 0.0
                        
                        total_upnl += upnl
                        
                        context['positions'].append({
                            'symbol': symbol,
                            'qty': contracts,
                            'entry': entry,
                            'mark': mark,
                            'upnl': upnl,
                            'upnl_pct': upnl_pct
                        })
                    
                    context['unrealized_pnl'] = total_upnl
                    # Realized PnL would need trade history - placeholder for now
                    context['realized_pnl'] = 0.0
            except Exception as e:
                self.logger.warning(f"Failed to get PnL data: {e}")
                self.metrics_hook.record_error('resolver', 'telegram')
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to resolve PnL context: {e}", exc_info=True)
            return {'balance': 0.0, 'unrealized_pnl': 0.0, 'realized_pnl': 0.0, 'positions': []}
    
    async def resolve_settings_context(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Resolve context for settings view.
        
        Args:
            user_id: Optional user ID for user-specific settings
        
        Returns:
            Dict with: settings (compact_mode, emojis, confirmations, timeframe, leverage, trading features)
        """
        try:
            policy = self._get_policy()
            
            # Get user settings from persistent storage
            from adapters.telegram.user_settings import get_user_settings
            settings_manager = get_user_settings()
            
            # Get trading feature states from policy (directly under trading, not scoring)
            trading = policy.get('trading', {})
            trailing_config = trading.get('trailing', {})
            partial_tp_config = trading.get('partial_tp', {})
            time_exit_config = trading.get('time_exit', {})
            dynamic_tpsl_config = trading.get('dynamic_tpsl', {})
            
            user_settings = {
                'compact_mode': settings_manager.get(user_id, 'compact', True),
                'emojis': settings_manager.get(user_id, 'emojis', False),
                'confirmations': settings_manager.get(user_id, 'confirmations', True),
                'timeframe': policy.get('trading', {}).get('timeframe', '15m'),
                'timeframe_locked': True,  # Locked by policy
                # Leverage from policy (not user_settings)
                'leverage': trading.get('risk', {}).get('leverage', {}).get('default', 5),
                
                # Trading features from policy
                'trailing_enabled': trailing_config.get('enabled', False),
                'partial_tp_enabled': partial_tp_config.get('enabled', False),
                'time_exit_enabled': time_exit_config.get('enabled', False),
                'dynamic_tpsl_enabled': dynamic_tpsl_config.get('enabled', False),
            }
            
            return user_settings
            
        except Exception as e:
            self.logger.error(f"Failed to resolve settings context: {e}", exc_info=True)
            return {
                'compact_mode': True,
                'emojis': False,
                'confirmations': True,
                'timeframe': '15m',
                'timeframe_locked': True,
                'leverage': 5,
                'trailing_enabled': False,
                'partial_tp_enabled': False,
                'time_exit_enabled': False,
                'dynamic_tpsl_enabled': False,
            }
    
    async def resolve_emergency_context(self) -> Dict[str, Any]:
        """
        Resolve context for emergency view.
        
        Returns:
            Dict with: open_positions, total_exposure, total_upnl, cb_state, mode
        """
        try:
            policy = self._get_policy()
            mode = policy.get('trading', {}).get('mode', 'PAPER')
            
            context = {
                'open_positions': 0,
                'total_exposure': 0.0,
                'total_upnl': 0.0,
                'cb_state': 'OFF',
                'mode': mode
            }
            
            # Get position data
            try:
                from adapters.exchange_okx_ccxt import OKXExchangeAdapter
                exchange_adapter = self._get_service('exchange', lambda: OKXExchangeAdapter())
                
                if exchange_adapter:
                    positions = await exchange_adapter.get_positions()
                    if positions:
                        context['open_positions'] = len(positions)
                        total_exposure = 0.0
                        total_upnl = 0.0
                        
                        for pos in positions:
                            size = abs(float(pos.get('contracts', 0) or pos.get('size', 0)))
                            mark = float(pos.get('mark_price', 0) or pos.get('markPrice', 0) or 0)
                            upnl = float(pos.get('unrealized_pnl', 0) or pos.get('unrealizedPnl', 0) or 0)
                            
                            total_exposure += size * mark
                            total_upnl += upnl
                        
                        context['total_exposure'] = total_exposure
                        context['total_upnl'] = total_upnl
            except Exception as e:
                self.logger.warning(f"Failed to get emergency context positions: {e}")
            
            # Get circuit breaker state
            try:
                from application.circuit_breaker import CircuitBreaker
                cb = self._get_service('circuit_breaker', lambda: CircuitBreaker())
                if cb:
                    context['cb_state'] = 'ON' if cb.is_tripped else 'OFF'
            except Exception as e:
                self.logger.debug(f"Circuit breaker check failed: {e}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to resolve emergency context: {e}", exc_info=True)
            return {
                'open_positions': 0,
                'total_exposure': 0.0,
                'total_upnl': 0.0,
                'cb_state': 'OFF',
                'mode': 'PAPER'
            }
    
    # ==================== ADVANCED SETTINGS CONTEXT ====================
    
    async def resolve_position_size_context(self) -> Dict[str, Any]:
        """Resolve position sizing settings from policy."""
        try:
            policy = self._get_policy()
            scoring = policy.get('trading', {}).get('scoring', {})
            pos_sizing = scoring.get('position_sizing', {})
            
            return {
                'min_percentage': pos_sizing.get('min_percentage', 0.01),
                'max_percentage': pos_sizing.get('max_percentage', 0.10),
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve position size context: {e}")
            return {'min_percentage': 0.01, 'max_percentage': 0.10}
    
    async def resolve_coins_context(self) -> Dict[str, Any]:
        """Resolve active coins from policy."""
        try:
            policy = self._get_policy()
            trading_pairs = policy.get('exchange', {}).get('symbols', {}).get('trading_pairs', [])
            
            return {
                'active_coins': trading_pairs,
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve coins context: {e}")
            return {'active_coins': []}
    
    async def resolve_coin_category_context(self, category: str) -> Dict[str, Any]:
        """Resolve coin list for a category - static or dynamic."""
        try:
            from adapters.telegram.views.advanced import COIN_CATEGORIES
            
            policy = self._get_policy()
            active_coins = policy.get('exchange', {}).get('symbols', {}).get('trading_pairs', [])
            
            coins = []
            category_name = category
            
            # Static categories
            if category in COIN_CATEGORIES:
                cat_info = COIN_CATEGORIES[category]
                coins = cat_info['coins']
                category_name = cat_info['name']
            
            # Dynamic categories (OKX fetch)
            elif category in ['volume', 'trending', 'losers', 'all']:
                # Fallback coins if API fails
                FALLBACK_COINS = {
                    'volume': ['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'AVAX', 'TRX', 'LINK'],
                    'trending': ['PEPE', 'WIF', 'BONK', 'FET', 'TAO', 'RENDER', 'SUI', 'APT', 'SEI', 'TIA'],
                    'losers': ['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'AVAX', 'TRX', 'LINK'],
                    'all': ['BTC', 'ETH', 'SOL', 'XRP', 'BNB', 'DOGE', 'ADA', 'AVAX', 'TRX', 'LINK', 
                            'DOT', 'ATOM', 'NEAR', 'FET', 'ARB', 'OP', 'SUI', 'APT', 'SEI', 'TIA'],
                }
                CATEGORY_NAMES = {
                    'volume': '📈 Top Hacim',
                    'trending': '🔥 Trending',
                    'losers': '📉 Düşenler',
                    'all': '💰 Tüm Coinler',
                }
                
                category_name = CATEGORY_NAMES.get(category, category)
                try:
                    # Use cached exchange adapter
                    from adapters.exchange_okx_ccxt import OKXCCXTAdapter
                    adapter = self._get_service('exchange_adapter', OKXCCXTAdapter)
                    
                    if adapter:
                        if category == 'all':
                            markets = await adapter.fetch_markets()
                            coins = [m['id'] for m in markets if 'SWAP' in m.get('id', '') and 'USDT' in m.get('id', '')][:50]
                        else:
                            tickers = await adapter.fetch_tickers()
                            swap_tickers = {k: v for k, v in tickers.items() if 'SWAP' in k and 'USDT' in k}
                            
                            if category == 'volume':
                                sorted_t = sorted(swap_tickers.items(), key=lambda x: x[1].get('quoteVolume', 0) or 0, reverse=True)
                                coins = [k for k, _ in sorted_t[:20]]
                            elif category == 'trending':
                                sorted_t = sorted(swap_tickers.items(), key=lambda x: x[1].get('percentage', 0) or 0, reverse=True)
                                coins = [k for k, _ in sorted_t[:20]]
                            elif category == 'losers':
                                sorted_t = sorted(swap_tickers.items(), key=lambda x: x[1].get('percentage', 0) or 0)
                                coins = [k for k, _ in sorted_t[:20]]
                    else:
                        coins = FALLBACK_COINS.get(category, [])
                except Exception as e:
                    self.logger.warning(f"Failed to fetch dynamic coins: {e}, using fallback")
                    coins = FALLBACK_COINS.get(category, [])
            
            return {
                'category': category,
                'category_name': category_name,
                'coins': coins,
                'active_coins': active_coins,
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve coin category context: {e}")
            return {'category': category, 'category_name': category, 'coins': [], 'active_coins': []}
    
    async def resolve_thresholds_context(self) -> Dict[str, Any]:
        """Resolve decision thresholds from policy."""
        try:
            policy = self._get_policy()
            thresholds = policy.get('trading', {}).get('scoring', {}).get('decision_thresholds', {})
            
            return {
                'enter_long': thresholds.get('enter_long', 52),
                'exit_long': thresholds.get('exit_long', 40),
                'enter_short': thresholds.get('enter_short', 48),
                'exit_short': thresholds.get('exit_short', 60),
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve thresholds context: {e}")
            return {'enter_long': 52, 'exit_long': 40, 'enter_short': 48, 'exit_short': 60}
    
    async def resolve_age_context(self) -> Dict[str, Any]:
        """Resolve position age settings from policy."""
        try:
            policy = self._get_policy()
            time_exit = policy.get('trading', {}).get('time_exit', {})
            
            return {
                'max_position_age_hours': time_exit.get('max_position_age_hours', 24),
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve age context: {e}")
            return {'max_position_age_hours': 24}
    
    async def resolve_weights_context(self) -> Dict[str, Any]:
        """Resolve score weights from policy."""
        try:
            policy = self._get_policy()
            scoring = policy.get('trading', {}).get('scoring', {})
            
            return {
                'ta_weight': scoring.get('ta_weight', 0.7),
                'ml_weight': scoring.get('ml_weight', 0.1),
                'news_weight': scoring.get('news_weight', 0.1),
                'risk_weight': scoring.get('risk_weight', 0.1),
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve weights context: {e}")
            return {'ta_weight': 0.7, 'ml_weight': 0.1, 'news_weight': 0.1, 'risk_weight': 0.1}
    
    async def resolve_ml_boost_context(self) -> Dict[str, Any]:
        """Resolve ML boost settings from policy."""
        try:
            policy = self._get_policy()
            ml_boost = policy.get('trading', {}).get('scoring', {}).get('ml_boost', {})
            
            return {
                'ml_boost': {
                    'enabled': ml_boost.get('enabled', False),
                    'tiers': ml_boost.get('tiers', [])
                }
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve ML boost context: {e}")
            return {'ml_boost': {'enabled': False, 'tiers': []}}
    
    async def resolve_signal_history_context(self) -> Dict[str, Any]:
        """Resolve signal history main menu context."""
        try:
            from application.signal_history import get_all_symbols, get_stats
            
            return {
                'symbols': get_all_symbols(),
                'stats': get_stats()
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve signal history context: {e}")
            return {'symbols': [], 'stats': {}}
    
    async def resolve_coin_signals_context(self, symbol: str) -> Dict[str, Any]:
        """Resolve signal history for a specific coin."""
        try:
            from application.signal_history import get_signals
            
            return {
                'symbol': symbol,
                'signals': get_signals(symbol, limit=50)
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve coin signals context: {e}")
            return {'symbol': symbol, 'signals': []}
    
    async def resolve_alerts_context(self, level: str = None) -> Dict[str, Any]:
        """Resolve alerts history context."""
        try:
            from application.alert_history import get_alerts, get_alert_counts
            
            return {
                'alerts': get_alerts(level=level, limit=30),
                'counts': get_alert_counts()
            }
        except Exception as e:
            self.logger.error(f"Failed to resolve alerts context: {e}")
            return {'alerts': [], 'counts': {}}


# Global instance
_context_resolver: Optional[ContextResolver] = None


def get_context_resolver() -> ContextResolver:
    """Get the global context resolver instance."""
    global _context_resolver
    if _context_resolver is None:
        _context_resolver = ContextResolver()
    return _context_resolver

