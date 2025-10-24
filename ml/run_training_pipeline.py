"""
ML Training Pipeline Orchestrator
Runs the complete ML training and deployment pipeline.
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd
from loguru import logger

from ml.binance_collector import BinanceDataCollector
from ml.feature_engineering import FeatureEngineer
from ml.train_lightgbm import LightGBMTrainer
from ml.model_version_manager import MLModelVersionManager
from ml.auto_deploy import MLAutoDeployer
from ml.ml_monitor import MLMonitor

class MLTrainingPipeline:
    """Orchestrates the complete ML model training and deployment pipeline."""

    def __init__(self):
        self.data_collector = BinanceDataCollector()
        self.feature_engineer = FeatureEngineer()
        self.model_manager = MLModelVersionManager()
        self.ml_monitor = MLMonitor()
        self.auto_deployer = MLAutoDeployer()
        self.trainer = LightGBMTrainer() # Default trainer
        
        self.pipeline_steps = [
            "data_collection",
            "feature_engineering",
            "model_training",
            "model_comparison",
            "auto_deployment"
        ]
    
    async def run_complete_pipeline(self) -> dict:
        """Run the complete ML training pipeline."""
        logger.info("🚀 Starting Complete ML Training Pipeline")
        logger.info("=" * 60)
        
        pipeline_results = {
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "final_status": "UNKNOWN",
            "steps": {},
            "error": None
        }
        
        try:
            # Step 1: Data Collection
            logger.info("📊 STEP 1: Data Collection")
            logger.info("-" * 40)
            all_data_dict = self.data_collector.collect_all_data()
            
            # Convert dict of DataFrames to a single DataFrame for training
            combined_df_list = []
            for symbol, timeframes_data in all_data_dict.items():
                for timeframe, df in timeframes_data.items():
                    if not df.empty:
                        # Reset index to make timestamp a column
                        df_reset = df.reset_index()
                        df_reset['symbol'] = symbol # Add symbol column
                        df_reset['timeframe'] = timeframe # Add timeframe column
                        combined_df_list.append(df_reset)
            
            if not combined_df_list:
                raise ValueError("No data collected for training.")
            
            combined_df = pd.concat(combined_df_list, ignore_index=True)
            combined_df = combined_df.sort_values(by=['timestamp', 'symbol', 'timeframe']).reset_index(drop=True)
            
            pipeline_results["steps"]["data_collection"] = {
                "status": "SUCCESS",
                "total_bars": len(combined_df),
                "symbols": list(combined_df['symbol'].unique())
            }
            logger.info(f"✅ Data Collection Completed. Total bars: {len(combined_df)}")
            logger.info("=" * 60)

            # Step 2: Feature Engineering
            logger.info("⚙️ STEP 2: Feature Engineering")
            logger.info("-" * 40)
            # Feature engineering is done inside the trainer's prepare_data method
            # We'll pass the combined_df to the trainer
            pipeline_results["steps"]["feature_engineering"] = {
                "status": "SUCCESS",
                "description": "Features will be engineered during model training."
            }
            logger.info("✅ Feature Engineering setup.")
            logger.info("=" * 60)

            # Step 3: Model Training (LightGBM)
            logger.info("🧠 STEP 3: Model Training (LightGBM)")
            logger.info("-" * 40)
            training_results = self.trainer.run_training_pipeline(combined_df, forward_bars=1)
            pipeline_results["steps"]["model_training"] = training_results
            logger.info(f"✅ Model Training Completed. Status: {training_results['status']}")
            logger.info("=" * 60)

            # Step 4: Model Comparison and Auto-Deployment
            logger.info("🚀 STEP 4: Model Comparison & Auto-Deployment")
            logger.info("-" * 40)
            if training_results["status"] == "SUCCESS":
                new_model_version = training_results["model_version"]
                new_model_metrics = training_results["metrics"]
                
                deploy_results = self.auto_deployer.compare_and_deploy(new_model_version, new_model_metrics)
                pipeline_results["steps"]["auto_deployment"] = deploy_results
                logger.info(f"✅ Auto-Deployment Completed. Status: {deploy_results['status']}")
            else:
                pipeline_results["steps"]["auto_deployment"] = {
                    "status": "SKIPPED",
                    "reason": "Model training failed or skipped."
                }
                logger.warning("⚠️ Auto-Deployment Skipped due to training issues.")
            logger.info("=" * 60)

            pipeline_results["final_status"] = "SUCCESS"

        except Exception as e:
            logger.error(f"❌ Pipeline failed at step: {e}")
            pipeline_results["final_status"] = "FAILED"
            pipeline_results["error"] = str(e)
        finally:
            pipeline_results["end_time"] = datetime.now().isoformat()
            self._save_pipeline_results(pipeline_results)
            logger.info("📄 Pipeline results saved.")
            logger.info("=" * 60)
        
        return pipeline_results

    def _save_pipeline_results(self, results: Dict[str, Any]):
        """Saves the pipeline results to a JSON file."""
        reports_dir = Path("reports")
        reports_dir.mkdir(parents=True, exist_ok=True)
        filepath = reports_dir / "ml_training_results.json"
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)

    def get_status_summary(self) -> str:
        """Generates a human-readable summary of the pipeline status."""
        summary = "\n📊 ML Training Pipeline Summary:\n"
        summary += "----------------------------------------\n"
        
        results_file = Path("reports/ml_training_results.json")
        if not results_file.exists():
            return "No pipeline results found."
        
        with open(results_file, 'r') as f:
            results = json.load(f)
        
        summary += f"Status: {results.get('final_status', 'UNKNOWN')}\n"
        if results.get('error'):
            summary += f"Error: {results['error']}\n"
        summary += f"Start Time: {results.get('start_time', 'N/A')}\n"
        summary += f"End Time: {results.get('end_time', 'N/A')}\n"
        
        summary += "\n--- Steps ---\n"
        for step_name, step_data in results.get('steps', {}).items():
            summary += f"  {step_name.replace('_', ' ').title()}: {step_data.get('status', 'UNKNOWN')}\n"
            if step_name == "data_collection" and step_data.get("total_bars"):
                summary += f"    Total Bars: {step_data['total_bars']}\n"
            if step_name == "model_training" and step_data.get("metrics"):
                metrics = step_data['metrics']
                summary += f"    AUC: {metrics.get('auc', 0):.3f}, Accuracy: {metrics.get('accuracy', 0):.3f}\n"
            if step_name == "auto_deployment" and step_data.get("reason"):
                summary += f"    Reason: {step_data['reason']}\n"
        
        summary += "\n--- Active Model ---\n"
        active_version = self.model_manager.get_active_model_version()
        if active_version:
            summary += f"  Active Model: {active_version}\n"
            active_metadata = self.model_manager.get_model_metadata(active_version)
            summary += f"  Active Model AUC: {active_metadata.get('metrics', {}).get('auc', 0):.3f}\n"
        else:
            summary += "  No active model.\n"
        
        summary += "\n--- Available Models ---\n"
        for model_name in self.model_manager.available_versions.keys():
            summary += f"  - {model_name}\n"
        
        return summary


async def main():
    """Main function to run the pipeline."""
    logger.info("🎯 ML Training Pipeline Starting...")
    
    # Initialize pipeline
    pipeline = MLTrainingPipeline()
    
    # Run complete pipeline
    results = await pipeline.run_complete_pipeline()
    
    # Print summary
    if results["final_status"] == "SUCCESS":
        logger.info(pipeline.get_status_summary())
    else:
        logger.error(f"Pipeline failed: {results.get('error', 'Unknown error')}")
    
    return results


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())