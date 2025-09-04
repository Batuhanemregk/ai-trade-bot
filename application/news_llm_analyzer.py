"""
News LLM Analyzer - Advanced LLM-based news classification and sentiment analysis
"""

import json
import re
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger
from openai import AsyncOpenAI
from adapters.llm_analyzer import LLMNewsAnalyzer


class NewsLLMAnalyzer:
    """Advanced LLM-based news analyzer with symbol classification and sentiment analysis"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.cache = {}  # Simple cache for repeated analysis
    
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
            
            # Prepare articles for analysis
            articles_text = self._prepare_articles_text(news_articles, symbol, symbol_aliases)
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(articles_text, symbol, symbol_aliases)
            
            # Get LLM analysis
            analysis_result = await self._get_llm_analysis(prompt)
            
            # Parse and validate result
            score, categories, rationale, volatility_impact = self._parse_analysis_result(analysis_result)
            
            logger.info(f"✅ [LLM] sym={symbol} analysis completed: {score:.1f} ({categories})")
            
            return score, categories, rationale, volatility_impact
            
        except Exception as e:
            logger.error(f"❌ [LLM] sym={symbol} analysis failed: {e}")
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
    
    async def _get_llm_analysis(self, prompt: str) -> str:
        """Get analysis from LLM"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional cryptocurrency market analyst. Provide accurate, objective sentiment analysis in the requested JSON format."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.3,  # Lower temperature for more consistent results
                timeout=30
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"LLM API request failed: {e}")
            raise
    
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
