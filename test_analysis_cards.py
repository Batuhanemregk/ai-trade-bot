"""
Test Analysis Cards - Hızlı analiz kartları testi
"""

import asyncio
import os
from dotenv import load_dotenv
from infrastructure.bootstrap import load_policy
from application.analysis_cards import AnalysisCardsService

async def test_analysis_cards():
    """Test analysis cards with sample data"""
    print("🧪 Testing Analysis Cards...")
    
    # Load environment and policy
    load_dotenv()
    policy = load_policy("configs/policy.yaml")
    
    # Initialize analysis cards service
    cards_service = AnalysisCardsService(policy)
    
    # Test startup message
    print("\n1️⃣ Testing Startup Message...")
    await cards_service.send_startup_message()
    
    # Test sample analysis results
    print("\n2️⃣ Testing Analysis Cards...")
    sample_results = [
        {
            'symbol': 'BTC-USDT-SWAP',
            'decision': 'LONG',
            'final_score': 75.5,
            'ta_score': 80.0,
            'ml_score': 70.0,
            'news_score': 85.0,
            'risk_score': 60.0,
            'news_info': {
                'type': 'positive',
                'confidence': 0.85,
                'title': 'Bitcoin ETF approved by SEC'
            },
            'risk_info': {
                'level': 'medium',
                'factors': ['volatility', 'liquidity']
            }
        },
        {
            'symbol': 'ETH-USDT-SWAP',
            'decision': 'SHORT',
            'final_score': 25.0,
            'ta_score': 20.0,
            'ml_score': 30.0,
            'news_score': 15.0,
            'risk_score': 40.0,
            'news_info': {
                'type': 'negative',
                'confidence': 0.70,
                'title': 'Ethereum network congestion issues'
            },
            'risk_info': {
                'level': 'high',
                'factors': ['correlation', 'volatility']
            }
        },
        {
            'symbol': 'SOL-USDT-SWAP',
            'decision': 'FLAT',
            'final_score': 50.0,
            'ta_score': 55.0,
            'ml_score': 45.0,
            'news_score': 50.0,
            'risk_score': 50.0,
            'news_info': {
                'type': 'neutral',
                'confidence': 0.60,
                'title': 'Solana ecosystem development continues'
            },
            'risk_info': {
                'level': 'low',
                'factors': ['liquidity']
            }
        }
    ]
    
    await cards_service.send_analysis_cards(sample_results)
    
    # Test shutdown message
    print("\n3️⃣ Testing Shutdown Message...")
    await cards_service.send_shutdown_message()
    
    print("\n🎯 Analysis cards test completed!")
    print("📱 Check your Telegram chat for messages")

if __name__ == "__main__":
    asyncio.run(test_analysis_cards())
