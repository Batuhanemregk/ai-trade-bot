"""
Haftalık Otomatik ML Training Script
Her hafta çalışacak şekilde scheduler'a eklenebilir.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ml.run_training_pipeline import MLTrainingPipeline

async def weekly_ml_training():
    """Haftalık ML training işlemi."""
    logger.info("🚀 Starting Weekly ML Training...")
    logger.info("=" * 60)
    
    try:
        # ML Training Pipeline'ı başlat
        pipeline = MLTrainingPipeline()
        results = await pipeline.run_complete_pipeline()
        
        # Sonuçları logla
        logger.info("📊 Weekly ML Training Results:")
        logger.info(f"Status: {results.get('final_status', 'UNKNOWN')}")
        
        if results.get('error'):
            logger.error(f"Error: {results['error']}")
        else:
            logger.info("✅ Weekly ML training completed successfully!")
            
            # Steps summary
            for step_name, step_data in results.get('steps', {}).items():
                status = step_data.get('status', 'UNKNOWN')
                logger.info(f"  {step_name.replace('_', ' ').title()}: {status}")
                
                if step_name == "data_collection" and step_data.get("total_bars"):
                    logger.info(f"    Total Bars: {step_data['total_bars']}")
                if step_name == "model_training" and step_data.get("metrics"):
                    metrics = step_data['metrics']
                    logger.info(f"    AUC: {metrics.get('auc', 0):.3f}")
                    logger.info(f"    Accuracy: {metrics.get('accuracy', 0):.3f}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Weekly ML training failed: {e}")
        return {"status": "FAILED", "error": str(e)}

def main():
    """Main function for weekly ML training."""
    logger.info(f"Weekly ML Training started at {datetime.now()}")
    
    # Run the async function
    results = asyncio.run(weekly_ml_training())
    
    logger.info(f"Weekly ML Training completed at {datetime.now()}")
    return results

if __name__ == "__main__":
    main()

