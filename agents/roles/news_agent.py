"""
News Agent for AiBotBS.
Performs news aggregation and sentiment analysis.
"""

import asyncio
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from domain.errors import AgentError

from ..core.base import BaseAgent, Message, MessageType
from ..core.tools import Tool, ToolCategory


@dataclass
class NewsItem:
    """News item with metadata."""
    id: str
    title: str
    content: str
    source: str
    url: str
    published_at: datetime
    sentiment_score: float = 0.0
    sentiment_label: str = "neutral"
    relevance_score: float = 0.0
    keywords: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SentimentAnalysis:
    """Sentiment analysis result."""
    overall_sentiment: str  # "positive", "negative", "neutral"
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    positive_keywords: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MarketSentiment:
    """Market sentiment summary."""
    symbol: str
    timestamp: datetime
    news_sentiment: SentimentAnalysis
    overall_sentiment: str
    confidence: float
    news_count: int
    recent_news: list[NewsItem] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class NewsAgent(BaseAgent):
    """News agent that aggregates news and performs sentiment analysis."""

    def __init__(self, agent_id: str, config: dict[str, Any]):
        super().__init__(agent_id, "news_agent", config)

        # News configuration
        self._news_sources = config.get("news_sources", [
            "cryptocompare", "coingecko", "cryptopanic", "mock"
        ])
        self._update_interval = config.get("update_interval", 300)  # 5 minutes
        self._max_news_items = config.get("max_news_items", 100)
        self._sentiment_thresholds = config.get("sentiment_thresholds", {
            "positive": 0.1,
            "negative": -0.1
        })

        # News storage
        self._news_cache: dict[str, list[NewsItem]] = {}
        self._sentiment_cache: dict[str, SentimentAnalysis] = {}
        self._market_sentiment: dict[str, MarketSentiment] = {}

        # Performance tracking
        self._news_processed = 0
        self._sentiment_analyzed = 0
        self._last_update = None

        # Sentiment keywords
        self._positive_keywords = config.get("positive_keywords", [
            "bullish", "surge", "rally", "breakout", "uptrend", "gains", "profit",
            "adoption", "partnership", "innovation", "growth", "success"
        ])
        self._negative_keywords = config.get("negative_keywords", [
            "bearish", "crash", "decline", "breakdown", "downtrend", "losses", "risk",
            "regulation", "ban", "hack", "scam", "failure", "bankruptcy"
        ])

        # Register message handlers
        self._register_message_handlers()

        # Register tools
        self._register_tools()

    async def _initialize(self) -> None:
        """Initialize the news agent."""
        self.logger.info("Initializing news agent")

        # Validate configuration
        self._validate_config()

        # Start news update loop
        asyncio.create_task(self._news_update_loop())

        # Start sentiment monitoring
        asyncio.create_task(self._sentiment_monitor())

        self.logger.info("News agent initialized")

    async def _cleanup(self) -> None:
        """Cleanup when stopping the agent."""
        self.logger.info("Cleaning up news agent")
        self.logger.info("News agent cleanup completed")

    def _register_message_handlers(self) -> None:
        """Register message handlers."""
        self.register_message_handler(MessageType.TASK, self._handle_task_message)
        self.register_message_handler(MessageType.DATA_UPDATE, self._handle_data_update)
        self.register_message_handler(MessageType.COMMAND, self._handle_command)

    def _register_tools(self) -> None:
        """Register news-specific tools."""
        from ..core.tools import get_tool_registry

        registry = get_tool_registry()
        registry.register_tool(NewsAggregationTool(self), ToolCategory.ANALYSIS)
        registry.register_tool(SentimentAnalysisTool(self), ToolCategory.ANALYSIS)
        registry.register_tool(MarketSentimentTool(self), ToolCategory.ANALYSIS)

    def _validate_config(self) -> None:
        """Validate agent configuration."""
        if not self._news_sources:
            self.logger.warning("No news sources configured")

        if self._update_interval < 60:
            self.logger.warning("Update interval too low, may cause rate limiting")

    async def _news_update_loop(self) -> None:
        """Main loop for updating news."""
        while self._running:
            try:
                await self._update_news()
                await asyncio.sleep(self._update_interval)
            except Exception as e:
                self.logger.error(f"News update loop error: {e}")
                await asyncio.sleep(60)  # Wait before retry

    async def _sentiment_monitor(self) -> None:
        """Monitor sentiment changes."""
        while self._running:
            try:
                await self._update_market_sentiment()
                await asyncio.sleep(600)  # Update every 10 minutes
            except Exception as e:
                self.logger.error(f"Sentiment monitor error: {e}")
                await asyncio.sleep(300)

    async def _update_news(self) -> None:
        """Update news from all sources."""
        try:
            self.logger.info("Updating news from sources")

            for source in self._news_sources:
                try:
                    news_items = await self._fetch_news_from_source(source)
                    if news_items:
                        self._news_cache[source] = news_items
                        self.logger.info(f"Fetched {len(news_items)} news items from {source}")
                except Exception as e:
                    self.logger.error(f"Failed to fetch news from {source}: {e}")

            self._last_update = datetime.utcnow()
            self.logger.info("News update completed")

        except Exception as e:
            self.logger.error(f"News update failed: {e}")

    async def _fetch_news_from_source(self, source: str) -> list[NewsItem]:
        """Fetch news from a specific source."""
        if source == "mock":
            return await self._fetch_mock_news()
        elif source == "cryptocompare":
            return await self._fetch_cryptocompare_news()
        elif source == "coingecko":
            return await self._fetch_coingecko_news()
        elif source == "cryptopanic":
            return await self._fetch_cryptopanic_news()
        else:
            self.logger.warning(f"Unknown news source: {source}")
            return []

    async def _fetch_mock_news(self) -> list[NewsItem]:
        """Fetch mock news for testing."""
        mock_news = [
            NewsItem(
                id=f"mock_{uuid4().hex[:8]}",
                title="Bitcoin Surges to New Highs",
                content="Bitcoin has reached new all-time highs as institutional adoption continues to grow.",
                source="mock",
                url="https://example.com/bitcoin-surge",
                published_at=datetime.utcnow() - timedelta(minutes=30),
                sentiment_score=0.7,
                sentiment_label="positive",
                keywords=["bitcoin", "surge", "adoption"]
            ),
            NewsItem(
                id=f"mock_{uuid4().hex[:8]}",
                title="Regulatory Concerns in Crypto Market",
                content="New regulations are causing uncertainty in the cryptocurrency market.",
                source="mock",
                url="https://example.com/regulations",
                published_at=datetime.utcnow() - timedelta(minutes=45),
                sentiment_score=-0.3,
                sentiment_label="negative",
                keywords=["regulations", "uncertainty", "crypto"]
            )
        ]
        return mock_news

    async def _fetch_cryptocompare_news(self) -> list[NewsItem]:
        """Fetch news from CryptoCompare API."""
        try:
            # This would be a real API call in production
            # For now, return mock data
            return await self._fetch_mock_news()
        except Exception as e:
            self.logger.error(f"CryptoCompare news fetch failed: {e}")
            return []

    async def _fetch_coingecko_news(self) -> list[NewsItem]:
        """Fetch news from CoinGecko API."""
        try:
            # This would be a real API call in production
            # For now, return mock data
            return await self._fetch_mock_news()
        except Exception as e:
            self.logger.error(f"CoinGecko news fetch failed: {e}")
            return []

    async def _fetch_cryptopanic_news(self) -> list[NewsItem]:
        """Fetch news from CryptoPanic API."""
        try:
            # This would be a real API call in production
            # For now, return mock data
            return await self._fetch_mock_news()
        except Exception as e:
            self.logger.error(f"CryptoPanic news fetch failed: {e}")
            return []

    async def _update_market_sentiment(self) -> None:
        """Update market sentiment for all tracked symbols."""
        try:
            # Get all unique symbols from news
            all_symbols = set()
            for news_list in self._news_cache.values():
                for news_item in news_list:
                    # Extract symbols from news content
                    symbols = self._extract_symbols_from_text(news_item.content)
                    all_symbols.update(symbols)

            # Update sentiment for each symbol
            for symbol in all_symbols:
                await self._calculate_market_sentiment(symbol)

        except Exception as e:
            self.logger.error(f"Market sentiment update failed: {e}")

    def _extract_symbols_from_text(self, text: str) -> list[str]:
        """Extract cryptocurrency symbols from text."""
        # Simple regex to find common crypto symbols
        symbol_pattern = r'\b(BTC|ETH|BNB|ADA|SOL|DOT|MATIC|LINK|UNI|AVAX)\b'
        symbols = re.findall(symbol_pattern, text.upper())
        return list(set(symbols))

    async def _calculate_market_sentiment(self, symbol: str) -> None:
        """Calculate market sentiment for a specific symbol."""
        try:
            # Collect all news related to this symbol
            symbol_news = []
            for news_list in self._news_cache.values():
                for news_item in news_list:
                    if symbol.lower() in news_item.content.lower() or symbol.lower() in news_item.title.lower():
                        symbol_news.append(news_item)

            if not symbol_news:
                return

            # Calculate overall sentiment
            sentiment_scores = [news.sentiment_score for news in symbol_news]
            overall_score = sum(sentiment_scores) / len(sentiment_scores)

            # Determine sentiment label
            if overall_score > self._sentiment_thresholds["positive"]:
                overall_sentiment = "positive"
            elif overall_score < self._sentiment_thresholds["negative"]:
                overall_sentiment = "negative"
            else:
                overall_sentiment = "neutral"

            # Create market sentiment
            market_sentiment = MarketSentiment(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                news_sentiment=SentimentAnalysis(
                    overall_sentiment=overall_sentiment,
                    sentiment_score=overall_score,
                    confidence=min(abs(overall_score), 1.0),
                    positive_keywords=self._extract_positive_keywords(symbol_news),
                    negative_keywords=self._extract_negative_keywords(symbol_news)
                ),
                overall_sentiment=overall_sentiment,
                confidence=min(abs(overall_score), 1.0),
                news_count=len(symbol_news),
                recent_news=symbol_news[:10]  # Keep last 10 news items
            )

            self._market_sentiment[symbol] = market_sentiment

        except Exception as e:
            self.logger.error(f"Failed to calculate market sentiment for {symbol}: {e}")

    def _extract_positive_keywords(self, news_items: list[NewsItem]) -> list[str]:
        """Extract positive keywords from news items."""
        keywords = []
        for news in news_items:
            for keyword in self._positive_keywords:
                if keyword.lower() in news.content.lower():
                    keywords.append(keyword)
        return list(set(keywords))

    def _extract_negative_keywords(self, news_items: list[NewsItem]) -> list[str]:
        """Extract negative keywords from news items."""
        keywords = []
        for news in news_items:
            for keyword in self._negative_keywords:
                if keyword.lower() in news.content.lower():
                    keywords.append(keyword)
        return list(set(keywords))

    async def _handle_task_message(self, message: Message) -> None:
        """Handle task messages."""
        try:
            task_type = message.body.get("task_type")

            if task_type == "news_aggregation":
                result = await self._aggregate_news(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="news_aggregation_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            elif task_type == "sentiment_analysis":
                result = await self._analyze_sentiment(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="sentiment_analysis_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            elif task_type == "market_sentiment":
                result = await self._get_market_sentiment(message.body)

                response = Message(
                    type=MessageType.RESULT,
                    from_agent=self.agent_id,
                    to_agent=message.from_agent,
                    subject="market_sentiment_result",
                    body=result,
                    reply_to=message.id
                )
                await self.send_message(response)

            else:
                self.logger.warning(f"Unknown task type: {task_type}")

        except Exception as e:
            self.logger.error(f"Error handling task message: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="task_error",
                body={"error": str(e)},
                reply_to=message.id
            )
            await self.send_message(error_response)

    async def _handle_data_update(self, message: Message) -> None:
        """Handle data update messages."""
        # Process external data updates
        data_type = message.body.get("data_type")
        if data_type == "external_news":
            await self._process_external_news(message.body)

    async def _handle_command(self, message: Message) -> None:
        """Handle command messages."""
        command = message.body.get("command")
        parameters = message.body.get("parameters", {})

        try:
            if command == "get_status":
                result = self.get_status()
            elif command == "get_news_sources":
                result = {"sources": self._news_sources}
            elif command == "get_news_count":
                result = {
                    "total_news": sum(len(news) for news in self._news_cache.values()),
                    "sources": {source: len(news) for source, news in self._news_cache.items()}
                }
            elif command == "force_update":
                await self._update_news()
                result = {"status": "updated", "timestamp": self._last_update.isoformat() if self._last_update else None}
            else:
                result = {"error": f"Unknown command: {command}"}

            response = Message(
                type=MessageType.RESULT,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject=f"command_response_{command}",
                body=result,
                reply_to=message.id
            )
            await self.send_message(response)

        except Exception as e:
            self.logger.error(f"Error handling command: {e}")
            error_response = Message(
                type=MessageType.ERROR,
                from_agent=self.agent_id,
                to_agent=message.from_agent,
                subject="command_error",
                body={"error": str(e)},
                reply_to=message.id
            )
            await self.send_message(error_response)

    async def _aggregate_news(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Aggregate news from all sources."""
        try:
            symbol = parameters.get("symbol")
            limit = parameters.get("limit", 50)
            time_filter = parameters.get("time_filter", "24h")

            # Collect all news
            all_news = []
            for news_list in self._news_cache.values():
                all_news.extend(news_list)

            # Filter by symbol if specified
            if symbol:
                filtered_news = []
                for news in all_news:
                    if (symbol.lower() in news.content.lower() or
                        symbol.lower() in news.title.lower()):
                        filtered_news.append(news)
                all_news = filtered_news

            # Filter by time
            if time_filter == "1h":
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
            elif time_filter == "24h":
                cutoff_time = datetime.utcnow() - timedelta(days=1)
            elif time_filter == "7d":
                cutoff_time = datetime.utcnow() - timedelta(days=7)
            else:
                cutoff_time = datetime.utcnow() - timedelta(days=1)

            recent_news = [news for news in all_news if news.published_at >= cutoff_time]

            # Sort by published time (newest first)
            recent_news.sort(key=lambda x: x.published_at, reverse=True)

            # Limit results
            recent_news = recent_news[:limit]

            # Convert to serializable format
            news_data = []
            for news in recent_news:
                news_data.append({
                    "id": news.id,
                    "title": news.title,
                    "content": news.content[:200] + "..." if len(news.content) > 200 else news.content,
                    "source": news.source,
                    "url": news.url,
                    "published_at": news.published_at.isoformat(),
                    "sentiment_score": news.sentiment_score,
                    "sentiment_label": news.sentiment_label,
                    "keywords": news.keywords
                })

            return {
                "symbol": symbol,
                "time_filter": time_filter,
                "news_count": len(news_data),
                "news": news_data,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"News aggregation failed: {e}")
            raise AgentError(f"News aggregation failed: {e}")

    async def _analyze_sentiment(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Analyze sentiment of text or news."""
        try:
            text = parameters.get("text")
            news_id = parameters.get("news_id")

            if not text and not news_id:
                raise AgentError("Missing required parameter: text or news_id")

            if news_id:
                # Find news item and analyze its content
                news_item = None
                for news_list in self._news_cache.values():
                    for news in news_list:
                        if news.id == news_id:
                            news_item = news
                            break
                    if news_item:
                        break

                if not news_item:
                    raise AgentError(f"News item not found: {news_id}")

                text = news_item.content

            # Perform sentiment analysis
            sentiment = await self._perform_sentiment_analysis(text)

            return {
                "text": text[:100] + "..." if len(text) > 100 else text,
                "sentiment": sentiment.overall_sentiment,
                "sentiment_score": sentiment.sentiment_score,
                "confidence": sentiment.confidence,
                "positive_keywords": sentiment.positive_keywords,
                "negative_keywords": sentiment.negative_keywords,
                "timestamp": sentiment.timestamp.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Sentiment analysis failed: {e}")
            raise AgentError(f"Sentiment analysis failed: {e}")

    async def _perform_sentiment_analysis(self, text: str) -> SentimentAnalysis:
        """Perform sentiment analysis on text."""
        try:
            text_lower = text.lower()

            # Count positive and negative keywords
            positive_count = sum(1 for keyword in self._positive_keywords if keyword.lower() in text_lower)
            negative_count = sum(1 for keyword in self._negative_keywords if keyword.lower() in text_lower)

            # Calculate sentiment score
            total_keywords = positive_count + negative_count
            if total_keywords == 0:
                sentiment_score = 0.0
            else:
                sentiment_score = (positive_count - negative_count) / total_keywords

            # Determine sentiment label
            if sentiment_score > self._sentiment_thresholds["positive"]:
                overall_sentiment = "positive"
            elif sentiment_score < self._sentiment_thresholds["negative"]:
                overall_sentiment = "negative"
            else:
                overall_sentiment = "neutral"

            # Extract keywords
            positive_keywords = [kw for kw in self._positive_keywords if kw.lower() in text_lower]
            negative_keywords = [kw for kw in self._negative_keywords if kw.lower() in text_lower]

            # Calculate confidence based on keyword presence
            confidence = min(abs(sentiment_score), 1.0)

            return SentimentAnalysis(
                overall_sentiment=overall_sentiment,
                sentiment_score=sentiment_score,
                confidence=confidence,
                positive_keywords=positive_keywords,
                negative_keywords=negative_keywords
            )

        except Exception as e:
            self.logger.error(f"Sentiment analysis calculation failed: {e}")
            return SentimentAnalysis(
                overall_sentiment="neutral",
                sentiment_score=0.0,
                confidence=0.0
            )

    async def _get_market_sentiment(self, parameters: dict[str, Any]) -> dict[str, Any]:
        """Get market sentiment for a symbol."""
        try:
            symbol = parameters.get("symbol")

            if not symbol:
                raise AgentError("Missing required parameter: symbol")

            if symbol not in self._market_sentiment:
                # Calculate sentiment if not available
                await self._calculate_market_sentiment(symbol)

            if symbol not in self._market_sentiment:
                return {
                    "symbol": symbol,
                    "error": "No sentiment data available"
                }

            sentiment = self._market_sentiment[symbol]

            return {
                "symbol": symbol,
                "overall_sentiment": sentiment.overall_sentiment,
                "sentiment_score": sentiment.news_sentiment.sentiment_score,
                "confidence": sentiment.confidence,
                "news_count": sentiment.news_count,
                "positive_keywords": sentiment.news_sentiment.positive_keywords,
                "negative_keywords": sentiment.news_sentiment.negative_keywords,
                "timestamp": sentiment.timestamp.isoformat()
            }

        except Exception as e:
            self.logger.error(f"Market sentiment retrieval failed: {e}")
            raise AgentError(f"Market sentiment retrieval failed: {e}")

    async def _process_external_news(self, data: dict[str, Any]) -> None:
        """Process external news updates."""
        try:
            # This could be news from webhooks or other external sources
            news_data = data.get("news", {})

            if news_data:
                # Create news item
                news_item = NewsItem(
                    id=news_data.get("id", f"external_{uuid4().hex[:8]}"),
                    title=news_data.get("title", ""),
                    content=news_data.get("content", ""),
                    source=news_data.get("source", "external"),
                    url=news_data.get("url", ""),
                    published_at=datetime.fromisoformat(news_data.get("published_at", datetime.utcnow().isoformat())),
                    keywords=news_data.get("keywords", [])
                )

                # Analyze sentiment
                sentiment = await self._perform_sentiment_analysis(news_item.content)
                news_item.sentiment_score = sentiment.sentiment_score
                news_item.sentiment_label = sentiment.overall_sentiment

                # Add to cache
                if "external" not in self._news_cache:
                    self._news_cache["external"] = []
                self._news_cache["external"].append(news_item)

                self.logger.info(f"Processed external news: {news_item.title}")

        except Exception as e:
            self.logger.error(f"Failed to process external news: {e}")

    def get_status(self) -> dict[str, Any]:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "agent_type": "news_agent",
            "status": self.status.value,
            "news_processed": self._news_processed,
            "sentiment_analyzed": self._sentiment_analyzed,
            "last_update": self._last_update.isoformat() if self._last_update else None,
            "news_sources": self._news_sources,
            "cached_news_count": sum(len(news) for news in self._news_cache.values()),
            "market_sentiment_count": len(self._market_sentiment),
            "update_interval": self._update_interval
        }


# Tool classes for the News agent

class NewsAggregationTool(Tool):
    """Tool for aggregating news."""

    def __init__(self, news_agent: NewsAgent):
        super().__init__("news_aggregation", "Aggregate news from multiple sources")
        self.news_agent = news_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute news aggregation."""
        return await self.news_agent._aggregate_news(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol to filter news by"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of news items to return"
            },
            "time_filter": {
                "type": "string",
                "enum": ["1h", "24h", "7d"],
                "description": "Time filter for news"
            }
        }


class SentimentAnalysisTool(Tool):
    """Tool for sentiment analysis."""

    def __init__(self, news_agent: NewsAgent):
        super().__init__("sentiment_analysis", "Analyze sentiment of text or news")
        self.news_agent = news_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute sentiment analysis."""
        return await self.news_agent._analyze_sentiment(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "text": {
                "type": "string",
                "description": "Text to analyze for sentiment"
            },
            "news_id": {
                "type": "string",
                "description": "ID of news item to analyze"
            }
        }


class MarketSentimentTool(Tool):
    """Tool for market sentiment analysis."""

    def __init__(self, news_agent: NewsAgent):
        super().__init__("market_sentiment", "Get market sentiment for a trading symbol")
        self.news_agent = news_agent

    async def execute(self, parameters: dict[str, Any], context: Any) -> Any:
        """Execute market sentiment analysis."""
        return await self.news_agent._get_market_sentiment(parameters)

    def _get_parameter_schema(self) -> dict[str, Any]:
        """Get parameter schema for the tool."""
        return {
            "symbol": {
                "type": "string",
                "description": "Trading symbol to get sentiment for"
            }
        }
