"""
News LLM Analyzer - Advanced LLM-based news classification and sentiment analysis
"""

import json
import os
import re
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger
from openai import AsyncOpenAI
from adapters.llm_analyzer import LLMNewsAnalyzer
from monitoring.prometheus_exporter import get_prometheus_exporter


class NewsLLMAnalyzer:
    """Advanced LLM-based news analyzer with symbol classification and sentiment analysis"""
    
    def __init__(self, api_key: str, model: str = None):
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Model selection (ENV override)
        self.model = model or os.getenv('NEWS_LLM_MODEL', 'gpt-4o-mini')  # Default: gpt-4o-mini (low cost)
        self.max_output_tokens = int(os.getenv('NEWS_MAX_OUTPUT_TOKENS', '128'))
        
        # Cost tracking (gpt-4o-mini pricing)
        self.cost_per_mtok_in = float(os.getenv('LLM_COST_PER_MTOK_IN', '0.15'))  # gpt-4o-mini: $0.15/1M
        self.cost_per_mtok_out = float(os.getenv('LLM_COST_PER_MTOK_OUT', '0.60'))  # gpt-4o-mini: $0.60/1M
        self.daily_budget_tokens = int(os.getenv('LLM_DAILY_BUDGET_TOKENS', '200000'))
        self.daily_budget_usd = float(os.getenv('LLM_DAILY_BUDGET_USD', '999.0'))  # High default (no limit)
        
        # Daily usage tracking (resets at midnight)
        self.daily_tokens_in = 0
        self.daily_tokens_out = 0
        self.daily_cost_usd = 0.0
        self.last_reset_date = self._get_current_date()
        self.budget_exceeded = False
        
        self.cache = {}  # Simple cache for repeated analysis
        
        # Log verbosity control
        self.verbose_logging = os.getenv('NEWS_VERBOSITY', 'summary').lower() == 'full'
        
        # Prometheus metrics
        self.metrics = get_prometheus_exporter()
    
    def _get_current_date(self) -> str:
        """Get current date as string for daily reset"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).strftime('%Y-%m-%d')
    
    def _check_and_reset_daily_budget(self):
        """Check if we need to reset daily budget (new day)"""
        current_date = self._get_current_date()
        if current_date != self.last_reset_date:
            logger.info(f"💰 Daily budget reset: {self.last_reset_date} → {current_date}")
            self.daily_tokens_in = 0
            self.daily_tokens_out = 0
            self.daily_cost_usd = 0.0
            self.last_reset_date = current_date
            self.budget_exceeded = False
    
    def _check_budget_exceeded(self) -> bool:
        """Check if daily budget is exceeded"""
        self._check_and_reset_daily_budget()
        
        # Check token budget
        total_tokens = self.daily_tokens_in + self.daily_tokens_out
        if total_tokens >= self.daily_budget_tokens:
            if not self.budget_exceeded:
                logger.warning(f"💰 Daily token budget exceeded: {total_tokens}/{self.daily_budget_tokens}")
                self.metrics.record_budget_trip("tokens")
                self.budget_exceeded = True
            return True
        
        # Check USD budget
        if self.daily_cost_usd >= self.daily_budget_usd:
            if not self.budget_exceeded:
                logger.warning(f"💰 Daily USD budget exceeded: ${self.daily_cost_usd:.4f}/${self.daily_budget_usd:.2f}")
                self.metrics.record_budget_trip("usd")
                self.budget_exceeded = True
            return True
        
        return False
    
    def _update_daily_usage(self, prompt_tokens: int, completion_tokens: int):
        """Update daily usage tracking"""
        self.daily_tokens_in += prompt_tokens
        self.daily_tokens_out += completion_tokens
        
        # Calculate cost
        cost = (prompt_tokens / 1_000_000 * self.cost_per_mtok_in) + \
               (completion_tokens / 1_000_000 * self.cost_per_mtok_out)
        self.daily_cost_usd += cost
        
        # Record Prometheus metrics
        self.metrics.record_llm_cost(cost)
    
    def get_daily_budget_status(self) -> Dict[str, Any]:
        """Get current daily budget status"""
        self._check_and_reset_daily_budget()
        
        total_tokens = self.daily_tokens_in + self.daily_tokens_out
        token_usage_pct = (total_tokens / self.daily_budget_tokens * 100) if self.daily_budget_tokens > 0 else 0
        usd_usage_pct = (self.daily_cost_usd / self.daily_budget_usd * 100) if self.daily_budget_usd < 999 else 0
        
        return {
            'tokens_in': self.daily_tokens_in,
            'tokens_out': self.daily_tokens_out,
            'total_tokens': total_tokens,
            'token_budget': self.daily_budget_tokens,
            'token_usage_pct': token_usage_pct,
            'cost_usd': self.daily_cost_usd,
            'budget_usd': self.daily_budget_usd,
            'usd_usage_pct': usd_usage_pct,
            'budget_exceeded': self.budget_exceeded,
            'budget_left_usd': max(0, self.daily_budget_usd - self.daily_cost_usd)
        }
    
    async def analyze_news_batch(
        self, 
        news_articles: List[Dict[str, Any]], 
        symbol: str,
        symbol_aliases: Dict[str, Any]
    ) -> Tuple[float, List[str], str, float]:
        """
        Analyze a batch of news articles for sentiment and symbol classification
        
        Returns:
            Tuple of (score, categories, rationale, volatility_impact)
        """
        try:
            if not news_articles:
                return self._neutral_score()
            
            # Budget check - if exceeded, return neutral score
            if self._check_budget_exceeded():
                logger.warning(f"💰 [LLM] sym={symbol} skipped - daily budget exceeded")
                self.metrics.record_news_items(len(news_articles), sent_to_llm=False, reason="budget_exceeded")
                return self._neutral_score()
            
            # Prepare articles for analysis
            articles_text = self._prepare_articles_text(news_articles, symbol, symbol_aliases)
            
            # Create analysis prompt (structured JSON)
            prompt = self._create_structured_prompt(articles_text, symbol, symbol_aliases)
            
            # Get LLM analysis
            analysis_result = await self._get_llm_analysis(prompt, symbol)
            
            # Parse and validate result (structured JSON)
            score, categories, rationale, volatility_impact = self._parse_structured_result(analysis_result)
            
            # Record metrics
            self.metrics.record_news_items(len(news_articles), sent_to_llm=True)
            
            if self.verbose_logging:
                logger.info(f"✅ [LLM] sym={symbol} analysis completed: {score:.1f} ({categories})")
            
            return score, categories, rationale, volatility_impact
            
        except Exception as e:
            logger.error(f"❌ [LLM] sym={symbol} analysis failed: {e}")
            self.metrics.record_news_items(len(news_articles), sent_to_llm=False, reason="error")
            return self._neutral_score()
    
    def _prepare_articles_text(self, articles: List[Dict[str, Any]], symbol: str, symbol_aliases: Dict[str, Any]) -> str:
        """Prepare articles text for LLM analysis"""
        articles_text = f"News articles about {symbol}:\n\n"
        
        for i, article in enumerate(articles[:10], 1):  # Limit to 10 articles
            title = article.get('title', 'No title')
            body = article.get('body', article.get('description', ''))
            url = article.get('url', '')
            
            # Clean and truncate text
            title = self._clean_text(title)
            body = self._clean_text(body)[:500]  # Limit body length
            
            articles_text += f"Article {i}:\n"
            articles_text += f"Title: {title}\n"
            articles_text += f"Content: {body}\n"
            if url:
                articles_text += f"URL: {url}\n"
            articles_text += "\n"
        
        return articles_text
    
    def _create_analysis_prompt(self, articles_text: str, symbol: str, symbol_aliases: Dict[str, Any]) -> str:
        """Create analysis prompt for LLM"""
        # Get symbol aliases for context
        aliases = symbol_aliases.get(symbol, {})
        cashtags = ", ".join(aliases.get('cashtags', []))
        names = ", ".join(aliases.get('names', []))
        
        prompt = f"""
You are a cryptocurrency market analyst. Analyze the following news articles about {symbol} and provide a comprehensive sentiment analysis.

Symbol Context:
- Ticker: {symbol}
- Cash Tags: {cashtags}
- Names: {names}

{articles_text}

Please analyze these articles and provide your response in the following JSON format:

{{
    "symbols": [
        {{"ticker": "{symbol}", "name": "{names.split(',')[0] if names else symbol}", "confidence": 0.92}}
    ],
    "classification": "symbol_specific|mixed|general",
    "direction": "positive|negative|neutral",
    "sentiment_score": <number between 0-100, where 0=very negative, 50=neutral, 100=very positive>,
    "categories": ["MARKET", "TECHNOLOGY", "REGULATION", "PARTNERSHIP", "SECURITY", "GENERAL"],
    "rationale": "<brief explanation of your analysis>",
    "volatility_impact": <number between 0-1, where 0=low volatility impact, 1=high volatility impact>
}}

Classification Rules:
- symbol_specific: News is specifically about {symbol} with high confidence (>0.7)
- mixed: News mentions multiple cryptocurrencies including {symbol} with moderate confidence (0.3-0.7)
- general: News is about general crypto market with low {symbol} relevance (<0.3)

Guidelines:
- Consider the overall sentiment across all articles
- Focus on market-moving news and significant developments
- Consider both positive and negative factors
- Assess potential impact on price volatility
- Be objective and data-driven
- Consider the specific context of {symbol}

Respond ONLY with the JSON object, no additional text.
"""
        return prompt
    
    def _create_structured_prompt(self, articles_text: str, symbol: str, symbol_aliases: Dict[str, Any]) -> str:
        """Create structured JSON prompt for cost-optimized LLM analysis"""
        # Get symbol aliases for context
        aliases = symbol_aliases.get(symbol, {})
        names = ", ".join(aliases.get('names', []))
        
        prompt = f"""Analyze crypto news for {symbol} ({names}). Return ONLY JSON:

{articles_text}

{{
    "sentiment": 0-100,
    "dir": "long|short|neutral",
    "impact": 0.0-1.0,
    "tags": ["MARKET"|"TECH"|"REG"|"PARTNER"|"SEC"|"GENERAL"]
}}

Rules:
- sentiment: 0=bearish, 50=neutral, 100=bullish
- dir: trading direction
- impact: volatility impact
- tags: max 3, most relevant

JSON only, no explanation."""
        return prompt
    
    async def _get_llm_analysis(self, prompt: str, symbol: str = "UNKNOWN") -> str:
        """Get analysis from LLM with detailed diagnostic logging and retry logic"""
        request_id = None
        
        # Check budget before making request
        if self._check_budget_exceeded():
            logger.warning(f"💰 Budget exceeded, skipping LLM request for {symbol}")
            return ""
        
        # Check if prompt is empty
        if not prompt or prompt.strip() == "":
            logger.warning(f"Empty prompt provided for {symbol}")
            return ""
        
        # Retry logic for failed requests
        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                # Ensure prompt is not empty and has reasonable length
                if len(prompt.strip()) < 10:
                    logger.error(f"Prompt too short for {symbol}: {len(prompt)} chars")
                    return ""
                
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a crypto analyst. Return only valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=self.max_output_tokens,  # gpt-4o-mini uses max_tokens
                    temperature=0.3,  # Low temperature for consistent output
                    response_format={"type": "json_object"},  # Force JSON output
                    timeout=30
                    )
                
                # Extract request ID from response headers if available
                if hasattr(response, '_headers'):
                    request_id = response._headers.get('x-request-id', 'unknown')
                
                # Log successful request
                self._log_llm_request_success(symbol, request_id, response)
                
                # Validate response structure
                if not response.choices or len(response.choices) == 0:
                    logger.error(f"No choices in LLM response for {symbol}")
                    return ""
                
                if not response.choices[0].message:
                    logger.error(f"No message in LLM response for {symbol}")
                    return ""
                
                # Check if response content is empty
                content = response.choices[0].message.content
                if not content or content.strip() == "":
                    logger.error(f"Empty LLM response content for symbol {symbol}")
                    return ""
                
                # Validate JSON structure
                try:
                    import json
                    json.loads(content)  # Test if it's valid JSON
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in LLM response for {symbol}: {e}")
                    return ""
                
                # Log response details for debugging
                if self.verbose_logging:
                    logger.debug(f"LLM response for {symbol}: {content[:100]}...")
                
                return content.strip()
                
            except Exception as e:
                # Log failed request with detailed diagnostics
                self._log_llm_request_error(symbol, request_id, e)
                
                # If this is the last attempt, raise the exception
                if attempt == max_retries:
                    logger.error(f"All {max_retries + 1} attempts failed for {symbol}")
                    raise
                
                # Wait before retry (exponential backoff)
                import asyncio
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Retrying LLM request for {symbol} in {wait_time}s (attempt {attempt + 1}/{max_retries + 1})")
                await asyncio.sleep(wait_time)
    
    def _log_llm_request_success(self, symbol: str, request_id: str, response):
        """Log successful LLM request with diagnostic info"""
        try:
            # Extract token usage if available
            usage = getattr(response, 'usage', None)
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0
            
            # Update daily usage tracking
            self._update_daily_usage(prompt_tokens, completion_tokens)
            
            # Record Prometheus metrics
            self.metrics.record_llm_request("2xx", self.model)
            self.metrics.record_llm_tokens(self.model, prompt_tokens, completion_tokens)
            
            # Get budget status
            budget_status = self.get_daily_budget_status()
            
            # Console summary
            logger.info(f"📊 [LLM] sym={symbol} req_id={request_id} tokens={prompt_tokens}+{completion_tokens} "
                       f"cost=${budget_status['cost_usd']:.4f} left=${budget_status['budget_left_usd']:.2f}")
            
            # File detail
            logger.debug(f"LLM_SUCCESS | symbol={symbol} | request_id={request_id} | "
                        f"model={self.model} | prompt_tokens={prompt_tokens} | "
                        f"completion_tokens={completion_tokens} | status=200 | "
                        f"daily_cost=${budget_status['cost_usd']:.4f}")
            
        except Exception as e:
            logger.debug(f"Error logging LLM success: {e}")
    
    def _log_llm_request_error(self, symbol: str, request_id: str, error):
        """Log failed LLM request with detailed diagnostics"""
        try:
            error_source = "internal_or_network"
            http_status = "unknown"
            error_type = "unknown"
            error_code = "unknown"
            error_message = str(error)
            retry_after = None
            
            # Parse OpenAI error details
            if hasattr(error, 'response'):
                response = error.response
                if hasattr(response, 'status_code'):
                    http_status = response.status_code
                
                # Check for rate limit headers
                if hasattr(response, 'headers'):
                    headers = response.headers
                    if 'x-ratelimit-limit-requests' in headers:
                        error_source = "openai_rate_limit"
                        retry_after = headers.get('retry-after')
                
                # Parse error body
                if hasattr(response, 'json'):
                    try:
                        error_data = response.json()
                        if 'error' in error_data:
                            error_info = error_data['error']
                            error_type = error_info.get('type', 'unknown')
                            error_code = error_info.get('code', 'unknown')
                            error_message = error_info.get('message', str(error))
                    except:
                        pass
            
            # Record Prometheus metrics
            if http_status == 429 and error_source == "openai_rate_limit":
                self.metrics.record_llm_request("4xx", self.model)
                self.metrics.record_llm_rate_limit("openai")
            elif http_status and str(http_status).startswith('4'):
                self.metrics.record_llm_request("4xx", self.model)
            elif http_status and str(http_status).startswith('5'):
                self.metrics.record_llm_request("5xx", self.model)
            else:
                self.metrics.record_llm_internal_error()
            
            # Console summary
            if error_source == "openai_rate_limit":
                logger.error(f"❌ [LLM] sym={symbol} req_id={request_id} status={http_status} rate_limit retry_after={retry_after}")
            else:
                logger.error(f"❌ [LLM] sym={symbol} req_id={request_id} status={http_status} {error_type}")
            
            # File detail
            logger.debug(f"LLM_ERROR | symbol={symbol} | request_id={request_id} | "
                        f"model={self.model} | http_status={http_status} | "
                        f"error_source={error_source} | error_type={error_type} | "
                        f"error_code={error_code} | retry_after={retry_after} | "
                        f"message={error_message[:200]}")
            
        except Exception as e:
            logger.debug(f"Error logging LLM error: {e}")
    
    def _parse_analysis_result(self, result: str) -> Tuple[float, List[str], str, float]:
        """Parse LLM analysis result"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', result, re.DOTALL)
            if not json_match:
                logger.warning("No JSON found in LLM response")
                return self._neutral_score()
            
            json_str = json_match.group(0)
            data = json.loads(json_str)
            
            # Extract and validate values
            score = float(data.get('sentiment_score', 50))
            score = max(0, min(100, score))  # Clamp to 0-100
            
            categories = data.get('categories', ['GENERAL'])
            if not isinstance(categories, list):
                categories = ['GENERAL']
            
            rationale = str(data.get('rationale', 'LLM analysis completed'))
            
            volatility_impact = float(data.get('volatility_impact', 0.5))
            volatility_impact = max(0, min(1, volatility_impact))  # Clamp to 0-1
            
            # Log classification details
            classification = data.get('classification', 'general')
            direction = data.get('direction', 'neutral')
            symbols = data.get('symbols', [])
            
            if symbols:
                symbol_info = symbols[0]
                confidence = symbol_info.get('confidence', 0.5)
                logger.info(f"📊 [NEWSCLS] type={classification} sym={symbol_info.get('ticker', 'UNKNOWN')} conf={confidence:.2f} dir={direction}")
            
            return score, categories, rationale, volatility_impact
            
        except Exception as e:
            logger.error(f"Failed to parse LLM analysis result: {e}")
            return self._neutral_score()
    
    def _parse_structured_result(self, result: str) -> Tuple[float, List[str], str, float]:
        """Parse structured JSON result from cost-optimized LLM"""
        try:
            # Check if result is empty or None
            if not result or result.strip() == "":
                logger.warning("Empty LLM response received, using neutral score")
                return self._neutral_score()
            
            # Parse JSON (already in JSON format due to response_format)
            data = json.loads(result)
            
            # Extract and validate values
            score = float(data.get('sentiment', 50))
            score = max(0, min(100, score))  # Clamp to 0-100
            
            direction = data.get('dir', 'neutral')
            categories = data.get('tags', ['GENERAL'])
            if not isinstance(categories, list):
                categories = ['GENERAL']
            
            volatility_impact = float(data.get('impact', 0.5))
            volatility_impact = max(0, min(1, volatility_impact))  # Clamp to 0-1
            
            # Create minimal rationale
            rationale = f"{direction.upper()} sentiment (score: {score:.1f}, impact: {volatility_impact:.2f})"
            
            return score, categories, rationale, volatility_impact
            
        except Exception as e:
            logger.error(f"Failed to parse structured LLM result: {e}")
            return self._neutral_score()
    
    def _clean_text(self, text: str) -> str:
        """Clean text for analysis"""
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s.,!?-]', '', text)
        
        return text.strip()
    
    def _neutral_score(self) -> Tuple[float, List[str], str, float]:
        """Return neutral score when analysis fails"""
        return (
            50.0,  # Neutral score
            ["GENERAL"],  # General category
            "Neutral (LLM analysis unavailable)",
            0.5  # Neutral volatility impact
        )
    
    def clear_cache(self):
        """Clear analysis cache"""
        self.cache.clear()
        logger.info("🗑️ LLM analysis cache cleared")
