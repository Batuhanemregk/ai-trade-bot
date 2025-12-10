"""
Cleanup Orphan Orders Job - Removes orphan TP/SL orders when position is closed

This job runs periodically to:
1. Fetch all open algo orders (TP/SL triggers)
2. Fetch all open positions
3. Cancel algo orders whose position no longer exists
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List
from loguru import logger

from application.jobs.base_job import BaseJob


class CleanupOrphanOrdersJob(BaseJob):
    """Job to clean up orphan TP/SL orders."""
    
    job_name = "cleanup_orphan_orders"
    description = "Remove orphan TP/SL orders when position is closed"
    
    def __init__(self):
        super().__init__()
        self.cleaned_count = 0
        self.last_run = None
    
    async def execute(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute orphan order cleanup.
        
        Args:
            context: Execution context containing exchange adapter
            
        Returns:
            Dict with cleanup results
        """
        try:
            self.last_run = datetime.now(timezone.utc)
            logger.info(f"🧹 [ORPHAN-CLEANUP] Starting orphan order cleanup...")
            
            # Get exchange adapter from context
            exchange_adapter = context.get('exchange_adapter') if context else None
            
            if not exchange_adapter:
                logger.warning("⚠️ [ORPHAN-CLEANUP] No exchange adapter in context, skipping")
                return {'status': 'skipped', 'reason': 'no_exchange_adapter'}
            
            # Step 1: Fetch all open positions
            open_positions = await self._fetch_open_positions(exchange_adapter)
            position_symbols = set(p.get('symbol', '') for p in open_positions if p.get('contracts', 0) != 0)
            
            logger.info(f"📊 [ORPHAN-CLEANUP] Open positions: {len(position_symbols)} symbols")
            
            # Step 2: Fetch all open algo orders
            open_algos = await self._fetch_open_algo_orders(exchange_adapter)
            
            logger.info(f"📋 [ORPHAN-CLEANUP] Open algo orders: {len(open_algos)}")
            
            # Step 3: Find orphan orders (algo orders without matching position)
            orphan_orders = []
            for algo in open_algos:
                algo_symbol = algo.get('symbol', '') or algo.get('instId', '')
                if algo_symbol not in position_symbols:
                    orphan_orders.append(algo)
            
            logger.info(f"🚫 [ORPHAN-CLEANUP] Found {len(orphan_orders)} orphan orders")
            
            # Step 4: Cancel orphan orders
            cancelled_count = 0
            for orphan in orphan_orders:
                success = await self._cancel_orphan_order(exchange_adapter, orphan)
                if success:
                    cancelled_count += 1
            
            self.cleaned_count += cancelled_count
            
            result = {
                'status': 'success',
                'open_positions': len(position_symbols),
                'open_algo_orders': len(open_algos),
                'orphan_orders_found': len(orphan_orders),
                'cancelled_count': cancelled_count,
                'total_cleaned': self.cleaned_count,
                'timestamp': self.last_run.isoformat()
            }
            
            if cancelled_count > 0:
                logger.info(f"✅ [ORPHAN-CLEANUP] Cancelled {cancelled_count} orphan orders")
            else:
                logger.info(f"✅ [ORPHAN-CLEANUP] No orphan orders to cancel")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ [ORPHAN-CLEANUP] Failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def _fetch_open_positions(self, exchange_adapter) -> List[Dict[str, Any]]:
        """Fetch all open positions from exchange."""
        try:
            if hasattr(exchange_adapter, 'fetch_positions'):
                positions = await exchange_adapter.fetch_positions()
            elif hasattr(exchange_adapter, 'ccxt_client'):
                positions = exchange_adapter.ccxt_client.fetch_positions()
            else:
                logger.warning("⚠️ [ORPHAN-CLEANUP] Cannot fetch positions")
                return []
            
            return positions or []
            
        except Exception as e:
            logger.error(f"❌ [ORPHAN-CLEANUP] Failed to fetch positions: {e}")
            return []
    
    async def _fetch_open_algo_orders(self, exchange_adapter) -> List[Dict[str, Any]]:
        """Fetch all open algo orders (TP/SL triggers)."""
        try:
            if hasattr(exchange_adapter, 'fetch_open_trigger_orders'):
                # Try fetching for all symbols
                algos = await exchange_adapter.fetch_open_trigger_orders(None)
            elif hasattr(exchange_adapter, 'ccxt_client'):
                # Use CCXT private API
                client = exchange_adapter.ccxt_client
                if hasattr(client, 'privateGetTradeOrdersAlgoPending'):
                    response = client.privateGetTradeOrdersAlgoPending({
                        'instType': 'SWAP',
                        'ordType': 'conditional'  # TP/SL orders
                    })
                    algos = response.get('data', [])
                else:
                    algos = []
            else:
                logger.warning("⚠️ [ORPHAN-CLEANUP] Cannot fetch algo orders")
                return []
            
            return algos or []
            
        except Exception as e:
            logger.error(f"❌ [ORPHAN-CLEANUP] Failed to fetch algo orders: {e}")
            return []
    
    async def _cancel_orphan_order(self, exchange_adapter, orphan: Dict[str, Any]) -> bool:
        """Cancel a single orphan order."""
        try:
            algo_id = orphan.get('algoId') or orphan.get('id') or orphan.get('orderId')
            symbol = orphan.get('symbol') or orphan.get('instId')
            client_id = orphan.get('algoClOrdId') or orphan.get('clientOrderId')
            
            logger.info(f"🗑️ [ORPHAN-CLEANUP] Cancelling orphan: {algo_id} ({symbol}) client={client_id}")
            
            if hasattr(exchange_adapter, 'cancel_algo_order'):
                result = await exchange_adapter.cancel_algo_order(symbol, algo_id)
                return True
            elif hasattr(exchange_adapter, 'ccxt_client'):
                client = exchange_adapter.ccxt_client
                if hasattr(client, 'privatePostTradeCancelAlgos'):
                    client.privatePostTradeCancelAlgos({
                        'algoId': algo_id,
                        'instId': symbol
                    })
                    return True
            
            logger.warning(f"⚠️ [ORPHAN-CLEANUP] Cannot cancel algo order: {algo_id}")
            return False
            
        except Exception as e:
            logger.error(f"❌ [ORPHAN-CLEANUP] Failed to cancel {orphan.get('algoId')}: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics."""
        return {
            'job_name': self.job_name,
            'total_cleaned': self.cleaned_count,
            'last_run': self.last_run.isoformat() if self.last_run else None
        }


# Job instance for scheduler registration
cleanup_orphan_orders_job = CleanupOrphanOrdersJob()


async def run_cleanup_orphan_orders(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Entry point for scheduler."""
    return await cleanup_orphan_orders_job.execute(context)
