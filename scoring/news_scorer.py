"""
News Scorer - Wrapper for news integration scoring
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from loguru import logger


class NewsScorer:
    """News sentiment scorer that wraps existing news integration."""

    def __init__(self):
        self.news_client = None
        self._initialize_news_client()

        # Keyword maps for sentiment analysis
        self.sentiment_keywords = {
            'SECURITY': {
                'positive': ['secure', 'safety', 'protection', 'defense', 'shield', 'guard'],
                'negative': ['hack', 'breach', 'vulnerability', 'attack', 'exploit', 'threat']
            },
            'REGULATION': {
                'positive': ['approval', 'compliance', 'legal', 'regulated', 'approved', 'clearance'],
                'negative': ['ban', 'restriction', 'prohibition', 'illegal', 'crackdown', 'enforcement']
            },
            'ADOPTION': {
                'positive': ['adoption', 'integration', 'partnership', 'collaboration', 'adoption', 'growth'],
                'negative': ['rejection', 'abandonment', 'discontinuation', 'replacement', 'migration']
            },
            'TECHNOLOGY': {
                'positive': ['innovation', 'upgrade', 'improvement', 'breakthrough', 'advancement', 'development'],
                'negative': ['bug', 'failure', 'downtime', 'outage', 'malfunction', 'defect']
            },
            'MARKET': {
                'positive': ['bullish', 'rally', 'surge', 'gain', 'profit', 'recovery'],
                'negative': ['bearish', 'crash', 'decline', 'loss', 'drop', 'correction']
            }
        }

    def _initialize_news_client(self):
        """Initialize news client with new LLM-based system."""
        try:
            # Import new news service
            from application.news_service import NewsService
            import os
            
            # Load policy for news service
            import yaml
            with open('configs/policy.yaml', 'r') as f:
                policy = yaml.safe_load(f)
            
            # Initialize news service
            self.news_service = NewsService(policy)
            logger.info("✅ News system initialized with LLM-based service")
            
        except Exception as e:
            logger.warning(f"⚠️ News service initialization failed, using simulated: {e}")
            self.news_client = SimulatedNewsClient()
            self.news_service = None

    async def score(self, symbol: str, lookback_minutes: int = 1440) -> tuple[float, list[str], str, float]:
        """
        Compute news sentiment score for a symbol using LLM-based news service.
        
        Args:
            symbol: Trading symbol
            lookback_minutes: Minutes to look back for news (default: 1440 = 24h)
            
        Returns:
            Tuple of (score: float, categories: List[str], rationale: str, volatility_impact: float)
        """
        try:
            # Use new news service if available
            if hasattr(self, 'news_service') and self.news_service:
                return await self.news_service.get_news_score(symbol)
            
            # Fallback to legacy system
            if not self.news_client:
                return self._neutral_score(symbol)

            # Get real news for the symbol
            headlines = await self._get_news_for_symbol(symbol, lookback_minutes)

            if not headlines:
                logger.warning(f"No news found for {symbol}")
                return self._neutral_score(symbol)

            logger.info(f"📰 Found {len(headlines)} news articles for {symbol}")

            # Use LLM analyzer if available, otherwise fallback
            if hasattr(self, 'llm_analyzer') and self.llm_analyzer:
                if hasattr(self.llm_analyzer, 'analyze_news_batch'):
                    # Check if it's async
                    if asyncio.iscoroutinefunction(self.llm_analyzer.analyze_news_batch):
                        # LLM analysis (async)
                        news_score, categories, rationale, volatility_impact = await self.llm_analyzer.analyze_news_batch(headlines, symbol)
                    else:
                        # Fallback analysis (sync)
                        news_score, categories, rationale, volatility_impact = self.llm_analyzer.analyze_news_batch(headlines, symbol)
                else:
                    # Fallback analysis
                    news_score, categories, rationale, volatility_impact = self.llm_analyzer.analyze_news_batch(headlines, symbol)
            else:
                # Legacy analysis
                category_scores = self._analyze_category_sentiment(headlines)
                news_score = self._compute_overall_score(category_scores)
                categories = self._get_relevant_categories(category_scores)
                rationale = self._generate_rationale(category_scores, news_score)
                volatility_impact = self._compute_volatility_impact(headlines, category_scores)

            logger.info(f"✅ News scoring completed for {symbol}: {news_score:.1f} ({categories})")

            return news_score, categories, rationale, volatility_impact

        except Exception as e:
            logger.error(f"❌ News scoring failed for {symbol}: {e}")
            return self._neutral_score(symbol)

    def _neutral_score(self, symbol: str) -> tuple[float, list[str], str, float]:
        """Return neutral score when news is not available."""
        return (
            50.0,  # Neutral score
            ["general"],  # General category
            "Neutral (no news data available)",
            0.5  # Neutral volatility impact
        )

    async def _get_news_for_symbol(self, symbol: str, lookback_minutes: int) -> list[Any]:
        """Get news headlines for a symbol within lookback period using real APIs."""
        try:
            if not self.news_client:
                return []

            # Use real news client if available
            if hasattr(self.news_client, 'get_news_for_symbol'):
                # MultiSourceNewsClient
                headlines = await self.news_client.get_news_for_symbol(symbol, limit=20)
            elif hasattr(self.news_client, 'get_news'):
                # Legacy simulated client
                headlines = self.news_client.get_news(symbol, lookback_minutes)
            else:
                # Fallback: try to get general crypto news
                headlines = await self._get_general_crypto_news()

            # Filter by time if possible
            if headlines and lookback_minutes < 1440:
                cutoff_time = datetime.now() - timedelta(minutes=lookback_minutes)
                headlines = self._filter_headlines_by_time(headlines, cutoff_time)

            return headlines

        except Exception as e:
            logger.error(f"News retrieval error for {symbol}: {e}")
            return []

    async def _get_general_crypto_news(self) -> list[Any]:
        """Get general crypto news as fallback."""
        try:
            # Try to get general market news
            if hasattr(self.news_client, 'get_market_news'):
                return await self.news_client.get_market_news()
            elif hasattr(self.news_client, 'get_latest_news'):
                return await self.news_client.get_latest_news()
            else:
                return []
        except:
            return []

    def _filter_headlines_by_time(self, headlines: list[Any], cutoff_time: datetime) -> list[Any]:
        """Filter headlines by time if they have timestamp information."""
        try:
            filtered = []
            for headline in headlines:
                # Try to extract timestamp from headline
                timestamp = self._extract_timestamp(headline)
                if timestamp and timestamp >= cutoff_time:
                    filtered.append(headline)
            return filtered
        except:
            return headlines

    def _extract_timestamp(self, headline: Any) -> datetime | None:
        """Extract timestamp from headline object."""
        try:
            if hasattr(headline, 'timestamp'):
                return headline.timestamp
            elif hasattr(headline, 'published_at'):
                return headline.published_at
            elif hasattr(headline, 'date'):
                return headline.date
            elif hasattr(headline, 'time'):
                return headline.time
            else:
                return None
        except:
            return None

    def _analyze_category_sentiment(self, headlines: list[Any]) -> dict[str, dict[str, float]]:
        """Analyze sentiment by category using keyword matching."""
        category_scores = {category: {'positive': 0, 'negative': 0, 'total': 0}
                          for category in self.sentiment_keywords.keys()}

        try:
            for headline in headlines:
                # Extract text from headline
                text = self._extract_headline_text(headline)
                if not text:
                    continue

                text_lower = text.lower()

                # Analyze each category
                for category, keywords in self.sentiment_keywords.items():
                    category_scores[category]['total'] += 1

                    # Count positive and negative keywords
                    positive_count = sum(1 for word in keywords['positive'] if word in text_lower)
                    negative_count = sum(1 for word in keywords['negative'] if word in text_lower)

                    if positive_count > negative_count:
                        category_scores[category]['positive'] += 1
                    elif negative_count > positive_count:
                        category_scores[category]['negative'] += 1

            # Convert counts to scores
            for category in category_scores:
                total = category_scores[category]['total']
                if total > 0:
                    positive_pct = category_scores[category]['positive'] / total
                    negative_pct = category_scores[category]['negative'] / total
                    # Score: 0-100 where 50 is neutral
                    category_scores[category]['score'] = 50 + (positive_pct - negative_pct) * 50
                else:
                    category_scores[category]['score'] = 50.0

            return category_scores

        except Exception as e:
            logger.error(f"Category sentiment analysis error: {e}")
            return {category: {'score': 50.0} for category in self.sentiment_keywords.keys()}

    def _extract_headline_text(self, headline: Any) -> str:
        """Extract text content from headline object."""
        try:
            if hasattr(headline, 'title'):
                return headline.title
            elif hasattr(headline, 'headline'):
                return headline.headline
            elif hasattr(headline, 'text'):
                return headline.text
            elif hasattr(headline, 'content'):
                return headline.content
            elif isinstance(headline, str):
                return headline
            else:
                return str(headline)
        except:
            return str(headline)

    def _compute_overall_score(self, category_scores: dict[str, dict[str, float]]) -> float:
        """Compute overall news sentiment score."""
        try:
            if not category_scores:
                return 50.0

            # Weight categories (market and regulation have higher impact)
            weights = {
                'MARKET': 0.35,
                'REGULATION': 0.25,
                'TECHNOLOGY': 0.20,
                'ADOPTION': 0.15,
                'SECURITY': 0.05
            }

            weighted_score = 0.0
            total_weight = 0.0

            for category, data in category_scores.items():
                if category in weights and 'score' in data:
                    weight = weights[category]
                    weighted_score += weight * data['score']
                    total_weight += weight

            if total_weight > 0:
                return weighted_score / total_weight
            else:
                return 50.0

        except Exception as e:
            logger.error(f"Overall score computation error: {e}")
            return 50.0

    def _get_relevant_categories(self, category_scores: dict[str, dict[str, float]]) -> list[str]:
        """Get categories with significant sentiment impact."""
        try:
            relevant = []
            for category, data in category_scores.items():
                if 'score' in data:
                    score = data['score']
                    if score > 70 or score < 30:  # Significant sentiment
                        relevant.append(category)

            if not relevant:
                relevant = ["general"]

            return relevant

        except Exception as e:
            logger.error(f"Relevant categories error: {e}")
            return ["general"]

    def _generate_rationale(self, category_scores: dict[str, dict[str, float]], overall_score: float) -> str:
        """Generate human-readable rationale for news sentiment."""
        try:
            rationale_parts = []

            # Add category breakdown
            for category, data in category_scores.items():
                if 'score' in data and 'total' in data and data['total'] > 0:
                    score = data['score']
                    if score > 70:
                        sentiment = "very positive"
                    elif score > 60:
                        sentiment = "positive"
                    elif score < 30:
                        sentiment = "very negative"
                    elif score < 40:
                        sentiment = "negative"
                    else:
                        sentiment = "neutral"

                    rationale_parts.append(f"{category}: {sentiment}")

            # Add overall assessment
            if overall_score > 70:
                overall = "Overall: Very bullish news sentiment"
            elif overall_score > 60:
                overall = "Overall: Bullish news sentiment"
            elif overall_score < 30:
                overall = "Overall: Very bearish news sentiment"
            elif overall_score < 40:
                overall = "Overall: Bearish news sentiment"
            else:
                overall = "Overall: Neutral news sentiment"

            rationale_parts.append(overall)

            return " | ".join(rationale_parts)

        except Exception as e:
            logger.error(f"Rationale generation error: {e}")
            return f"News score: {overall_score:.1f} (analysis error)"

    def _compute_volatility_impact(self, headlines: list[Any], category_scores: dict[str, dict[str, float]]) -> float:
        """Compute volatility impact based on news sentiment and volume."""
        try:
            if not headlines:
                return 0.5  # Neutral impact

            # Base volatility from sentiment extremes
            volatility_score = 0.5

            # Check for extreme sentiment categories
            for category, data in category_scores.items():
                if 'score' in data:
                    score = data['score']
                    if score > 80 or score < 20:  # Extreme sentiment
                        volatility_score += 0.2
                    elif score > 70 or score < 30:  # Strong sentiment
                        volatility_score += 0.1

            # Volume impact (more news = higher potential volatility)
            news_volume = len(headlines)
            if news_volume > 10:
                volatility_score += 0.2
            elif news_volume > 5:
                volatility_score += 0.1

            # Regulation and market news have higher volatility impact
            for high_impact_category in ['REGULATION', 'MARKET']:
                if high_impact_category in category_scores:
                    data = category_scores[high_impact_category]
                    if 'score' in data and abs(data['score'] - 50) > 20:
                        volatility_score += 0.1

            # Ensure volatility impact is between 0 and 1
            return max(0.0, min(1.0, volatility_score))

        except Exception as e:
            logger.error(f"Volatility impact computation error: {e}")
            return 0.5


class SimulatedNewsClient:
    """Simulated news client for when real news integration is not available."""
    
    def __init__(self):
        self.available = True
    
    def is_available(self) -> bool:
        return self.available
    
    def get_news(self, symbol: str, lookback_minutes: int = 1440) -> list[dict]:
        """Simulate news headlines for a symbol."""
        import random
        import time
        
        # Generate simulated news based on symbol and time
        current_time = int(time.time())
        symbol_hash = hash(symbol) % 100
        
        # Create some simulated headlines
        headlines = []
        
        # Market sentiment headlines
        if symbol_hash > 70:
            headlines.append({
                'title': f'Positive sentiment for {symbol}',
                'category': 'MARKET',
                'sentiment': 'positive',
                'timestamp': current_time - random.randint(0, lookback_minutes * 60)
            })
        elif symbol_hash < 30:
            headlines.append({
                'title': f'Negative sentiment for {symbol}',
                'category': 'MARKET',
                'sentiment': 'negative',
                'timestamp': current_time - random.randint(0, lookback_minutes * 60)
            })
        
        # Technology headlines
        if random.random() > 0.7:
            headlines.append({
                'title': f'Technology update for {symbol}',
                'category': 'TECHNOLOGY',
                'sentiment': random.choice(['positive', 'negative', 'neutral']),
                'timestamp': current_time - random.randint(0, lookback_minutes * 60)
            })
        
        # Regulation headlines (less frequent but high impact)
        if random.random() > 0.9:
            headlines.append({
                'title': f'Regulatory news for {symbol}',
                'category': 'REGULATION',
                'sentiment': random.choice(['positive', 'negative']),
                'timestamp': current_time - random.randint(0, lookback_minutes * 60)
            })
        
        return headlines
    
    def get_news_for_symbol(self, symbol: str) -> list[dict]:
        """Get news for a specific symbol (alias for get_news)."""
        return self.get_news(symbol)
    
    def get_market_news(self) -> list[dict]:
        """Get general market news."""
        return self.get_news("MARKET", 1440)
    
    def get_latest_news(self) -> list[dict]:
        """Get latest news."""
        return self.get_news("LATEST", 60)


# Global instance
news_scorer = NewsScorer()
