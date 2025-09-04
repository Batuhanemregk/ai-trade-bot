"""
LLM-based News Sentiment Analyzer using OpenAI ChatGPT API
"""

import asyncio
import json
import re
from typing import List, Dict, Any, Tuple, Optional
from loguru import logger
import openai
from openai import AsyncOpenAI


class LLMNewsAnalyzer:
    """Analyzes news sentiment using OpenAI ChatGPT API"""
    
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.cache = {}  # Simple cache for repeated analysis
    
    async def analyze_news_batch(self, news_articles: List[Dict[str, Any]], symbol: str) -> Tuple[float, List[str], str, float]:
        """
        Analyze a batch of news articles for sentiment
        
        Returns:
            Tuple of (score, categories, rationale, volatility_impact)
        """
        try:
            if not news_articles:
                return self._neutral_score()
            
            # Check cache first
            cache_key = f"{symbol}_{len(news_articles)}_{hash(str(news_articles[:3]))}"
            if cache_key in self.cache:
                logger.debug(f"Using cached analysis for {symbol}")
                return self.cache[cache_key]
            
            # Prepare articles for analysis
            articles_text = self._prepare_articles_text(news_articles, symbol)
            
            # Create analysis prompt
            prompt = self._create_analysis_prompt(articles_text, symbol)
            
            # Get LLM analysis
            analysis_result = await self._get_llm_analysis(prompt)
            
            # Parse and validate result
            score, categories, rationale, volatility_impact = self._parse_analysis_result(analysis_result)
            
            # Cache result
            self.cache[cache_key] = (score, categories, rationale, volatility_impact)
            
            logger.info(f"✅ LLM analysis completed for {symbol}: {score:.1f} ({categories})")
            
            return score, categories, rationale, volatility_impact
            
        except Exception as e:
            logger.error(f"❌ LLM analysis failed for {symbol}: {e}")
            return self._neutral_score()
    
    def _prepare_articles_text(self, articles: List[Dict[str, Any]], symbol: str) -> str:
        """Prepare articles text for LLM analysis"""
        articles_text = f"News articles about {symbol}:\n\n"
        
        for i, article in enumerate(articles[:10], 1):  # Limit to 10 articles
            title = article.get('title', 'No title')
            body = article.get('body', article.get('description', ''))
            
            # Clean and truncate text
            title = self._clean_text(title)
            body = self._clean_text(body)[:500]  # Limit body length
            
            articles_text += f"Article {i}:\n"
            articles_text += f"Title: {title}\n"
            articles_text += f"Content: {body}\n\n"
        
        return articles_text
    
    def _create_analysis_prompt(self, articles_text: str, symbol: str) -> str:
        """Create analysis prompt for LLM"""
        prompt = f"""
You are a cryptocurrency market analyst. Analyze the following news articles about {symbol} and provide a sentiment analysis.

{articles_text}

Please analyze these articles and provide your response in the following JSON format:

{{
    "sentiment_score": <number between 0-100, where 0=very negative, 50=neutral, 100=very positive>,
    "categories": ["MARKET", "TECHNOLOGY", "REGULATION", "PARTNERSHIP", "SECURITY", "GENERAL"],
    "rationale": "<brief explanation of your analysis>",
    "volatility_impact": <number between 0-1, where 0=low volatility impact, 1=high volatility impact>
}}

Guidelines:
- Consider the overall sentiment across all articles
- Focus on market-moving news and significant developments
- Consider both positive and negative factors
- Assess potential impact on price volatility
- Be objective and data-driven

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
                max_tokens=500,
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
        logger.info("LLM analysis cache cleared")


class FallbackNewsAnalyzer:
    """Fallback analyzer when LLM is not available"""
    
    def __init__(self):
        self.keyword_sentiment = {
            # Positive keywords
            'positive': ['bullish', 'surge', 'rally', 'breakthrough', 'partnership', 'adoption', 'upgrade', 'launch', 'success', 'growth', 'profit', 'gain', 'rise', 'increase', 'positive', 'optimistic', 'strong', 'robust', 'excellent', 'outstanding'],
            
            # Negative keywords  
            'negative': ['bearish', 'crash', 'decline', 'fall', 'drop', 'loss', 'hack', 'security', 'breach', 'regulation', 'ban', 'restriction', 'concern', 'risk', 'volatile', 'uncertain', 'negative', 'pessimistic', 'weak', 'poor', 'bad', 'terrible'],
            
            # Volatility keywords
            'volatility': ['volatile', 'volatility', 'uncertainty', 'fluctuation', 'swing', 'dramatic', 'sharp', 'sudden', 'rapid', 'extreme', 'wild', 'turbulent']
        }
    
    def analyze_news_batch(self, news_articles: List[Dict[str, Any]], symbol: str) -> Tuple[float, List[str], str, float]:
        """Analyze news using keyword-based sentiment"""
        try:
            if not news_articles:
                return self._neutral_score()
            
            total_score = 0
            total_volatility = 0
            categories = set()
            article_count = 0
            
            for article in news_articles:
                title = article.get('title', '').lower()
                body = article.get('body', article.get('description', '')).lower()
                text = f"{title} {body}"
                
                # Calculate sentiment
                positive_count = sum(1 for word in self.keyword_sentiment['positive'] if word in text)
                negative_count = sum(1 for word in self.keyword_sentiment['negative'] if word in text)
                volatility_count = sum(1 for word in self.keyword_sentiment['volatility'] if word in text)
                
                # Calculate article score
                if positive_count + negative_count > 0:
                    article_score = 50 + ((positive_count - negative_count) / (positive_count + negative_count)) * 50
                else:
                    article_score = 50
                
                total_score += article_score
                total_volatility += min(1.0, volatility_count * 0.2)
                article_count += 1
                
                # Determine categories
                if any(word in text for word in ['market', 'price', 'trading', 'bull', 'bear']):
                    categories.add('MARKET')
                if any(word in text for word in ['technology', 'upgrade', 'update', 'protocol', 'network']):
                    categories.add('TECHNOLOGY')
                if any(word in text for word in ['regulation', 'sec', 'government', 'legal', 'compliance']):
                    categories.add('REGULATION')
                if any(word in text for word in ['partnership', 'collaboration', 'integration', 'alliance']):
                    categories.add('PARTNERSHIP')
                if any(word in text for word in ['security', 'hack', 'breach', 'vulnerability']):
                    categories.add('SECURITY')
            
            if article_count == 0:
                return self._neutral_score()
            
            # Calculate averages
            avg_score = total_score / article_count
            avg_volatility = total_volatility / article_count
            
            # Ensure categories
            if not categories:
                categories = {'GENERAL'}
            
            rationale = f"Keyword-based analysis of {article_count} articles"
            
            return avg_score, list(categories), rationale, avg_volatility
            
        except Exception as e:
            logger.error(f"Fallback analysis failed for {symbol}: {e}")
            return self._neutral_score()
    
    def _neutral_score(self) -> Tuple[float, List[str], str, float]:
        """Return neutral score"""
        return (
            50.0,
            ["GENERAL"],
            "Neutral (fallback analysis)",
            0.5
        )
