"""
5-minute incremental news update job
"""

import asyncio
from typing import Dict, Any
from loguru import logger

from application.jobs.base_job import BaseJob
from application.news_service import NewsService


class NewsIncremental5mJob(BaseJob):
    """5-minute incremental news update job"""
    
    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.news_service = None
    
    async def initialize(self):
        """Initialize the job"""
        self.news_service = NewsService(self.policy)
        logger.info("✅ NewsIncremental5mJob initialized")
    
    async def execute(self):
        """Execute incremental news update"""
        try:
            if not self.news_service:
                logger.error("❌ News service not initialized")
                return
            
            # Get symbols from policy (exchange.symbols.supported_pairs)
            symbols = (
                self.policy.get('exchange', {})
                .get('symbols', {})
                .get('supported_pairs', [])
            )
            if not symbols:
                logger.warning("⚠️ No symbols configured for news update")
                return
            
            # On-start bootstrap if no watermarks exist
            await self.news_service.ensure_bootstrap_on_start(symbols)
            
            # Run incremental update
            await self.news_service.incremental_update_symbols(symbols)
            
            # Log statistics
            stats = self.news_service.get_news_stats()
            logger.info(f"📊 News service stats: {stats}")
            
        except Exception as e:
            logger.error(f"❌ NewsIncremental5mJob execution failed: {e}")
            raise
    
    async def cleanup(self):
        """Cleanup news service resources"""
        try:
            if self.news_service:
                await self.news_service.close()
                logger.debug("✅ NewsIncremental5mJob cleanup completed")
        except Exception as e:
            logger.error(f"❌ NewsIncremental5mJob cleanup failed: {e}")