import asyncio
from typing import Dict, Any

from loguru import logger

from application.jobs.base_job import BaseJob
from application.analysis_cards import AnalysisCardsService
from application.analysis_cards_state import get_latest_analysis


class TelegramSummary15mJob(BaseJob):
    """Job responsible for ensuring Telegram analysis summary is published once per bar."""

    def __init__(self, policy: Dict[str, Any], semaphore: asyncio.Semaphore, runtime_state: Dict[str, Any]):
        super().__init__(policy, semaphore, runtime_state)
        self.analysis_cards: AnalysisCardsService | None = None

    async def initialize(self, exchange_adapter=None):
        """Initialize analysis cards service."""
        self.exchange_adapter = exchange_adapter
        self.analysis_cards = AnalysisCardsService(self.policy)
        logger.info("✅ TelegramSummary15mJob initialized")

    async def cleanup(self):
        """Cleanup telegram resources."""
        try:
            if self.analysis_cards and getattr(self.analysis_cards, "telegram_client", None):
                await self.analysis_cards.telegram_client.stop()
                logger.debug("✅ Closed telegram client for TelegramSummary15mJob")
        except Exception as exc:
            logger.error(f"❌ TelegramSummary15mJob cleanup failed: {exc}")

    async def execute(self):
        """Publish summary card for current 15m bar if not already emitted."""
        if not self.start_run('15m'):
            return

        bar_id = self.current_bar_id
        try:
            logger.info(f"[JOB] name=telegram_summary_15m run_id={self.run_id} bar={bar_id} status=STARTING")

            if not self.analysis_cards:
                logger.warning("⚠️ Analysis cards service not initialized; skipping")
                self.finish_run("SUCCESS")
                return
            if not self.analysis_cards.is_enabled:
                logger.info("ℹ️ Analysis cards disabled via policy; skipping")
                self.finish_run("SUCCESS")
                return

            latest = get_latest_analysis()
            if not latest:
                logger.info(f"[JOB] name=telegram_summary_15m run_id={self.run_id} bar={bar_id} no analysis snapshot yet")
                self.finish_run("SUCCESS")
                return

            if latest.get('bar_id') != bar_id:
                logger.info(
                    f"[JOB] name=telegram_summary_15m run_id={self.run_id} bar={bar_id} "
                    f"latest_bar={latest.get('bar_id')} mismatch, skipping"
                )
                self.finish_run("SUCCESS")
                return

            if self.is_bar_already_processed(self.job_id, '15m'):
                logger.info(
                    f"[JOB] name=telegram_summary_15m run_id={self.run_id} bar={bar_id} "
                    "already published → skipping"
                )
                self.finish_run("SUCCESS")
                return

            await self.analysis_cards.publish_latest_summary()
            self.mark_bar_processed(self.job_id, '15m')

            logger.info(f"[JOB] name=telegram_summary_15m run_id={self.run_id} bar={bar_id} status=SUCCESS")
            self.finish_run("SUCCESS")

        except Exception as exc:
            logger.error(f"[JOB] name=telegram_summary_15m status=FAIL error={exc}")
            self.finish_run("FAILED", str(exc))
