"""
Parameter optimization for backtest strategy.
Tests different position sizes, stop loss, and take profit levels.
"""

import asyncio
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger
import json
from datetime import datetime

from backtests.engine import BacktestEngine
from configs.policy import load_policy


class ParameterOptimizer:
    """Optimize backtest parameters."""
    
    def __init__(self, data_file: str, symbol: str, initial_capital: float = 10000.0):
        self.data_file = data_file
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.results = []
    
    async def test_configuration(
        self,
        position_size: float,
        stop_loss: float,
        take_profit: float,
        config_name: str
    ) -> Dict[str, Any]:
        """Test a specific configuration."""
        
        logger.info(f"\nTesting: {config_name}")
        logger.info(f"  Position Size: {position_size*100:.1f}%")
        logger.info(f"  Stop Loss: {stop_loss*100:.1f}%")
        logger.info(f"  Take Profit: {take_profit*100:.1f}%")
        
        # Load and modify policy
        policy = load_policy()
        policy['trading']['risk']['max_position_size'] = position_size
        policy['trading']['risk']['stop_loss_pct'] = stop_loss
        policy['trading']['risk']['take_profit_pct'] = take_profit
        
        # Create temporary policy file
        import tempfile
        import yaml
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(policy, f)
            temp_policy_path = f.name
        
        try:
            # Run backtest
            engine = BacktestEngine(
                policy_path=temp_policy_path,
                initial_capital=self.initial_capital
            )
            
            results = await engine.run(
                data_file=self.data_file,
                symbol=self.symbol
            )
            
            metrics = results['metrics']
            
            # Store results
            result = {
                'config_name': config_name,
                'position_size': position_size,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'total_return': metrics['total_return'],
                'sharpe_ratio': metrics['sharpe_ratio'],
                'sortino_ratio': metrics['sortino_ratio'],
                'max_drawdown_pct': metrics['max_drawdown_pct'],
                'win_rate': metrics['win_rate'],
                'total_trades': metrics['total_trades'],
                'profit_factor': metrics.get('profit_factor', 0),
                'expectancy': metrics.get('expectancy', 0),
                'final_capital': metrics.get('final_capital', 0)
            }
            
            self.results.append(result)
            
            logger.info(f"  Return: {metrics['total_return']:.2f}%")
            logger.info(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
            logger.info(f"  Win Rate: {metrics['win_rate']:.1f}%")
            logger.info(f"  Max DD: {metrics['max_drawdown_pct']:.2f}%")
            
            return result
            
        finally:
            # Clean up temp file
            import os
            if os.path.exists(temp_policy_path):
                os.unlink(temp_policy_path)
    
    async def run_optimization(self):
        """Run optimization with different parameter combinations."""
        
        logger.info("\n" + "="*60)
        logger.info("PARAMETER OPTIMIZATION")
        logger.info("="*60)
        
        # Parameter grid
        position_sizes = [0.05, 0.10, 0.15]  # 5%, 10%, 15%
        stop_losses = [0.015, 0.020, 0.025]  # 1.5%, 2%, 2.5%
        take_profits = [0.03, 0.04, 0.05]    # 3%, 4%, 5%
        
        total_tests = len(position_sizes) * len(stop_losses) * len(take_profits)
        logger.info(f"\nTotal configurations to test: {total_tests}")
        logger.info(f"  Position Sizes: {[f'{p*100:.0f}%' for p in position_sizes]}")
        logger.info(f"  Stop Losses: {[f'{s*100:.1f}%' for s in stop_losses]}")
        logger.info(f"  Take Profits: {[f'{t*100:.0f}%' for t in take_profits]}")
        
        test_num = 0
        
        for pos_size in position_sizes:
            for stop_loss in stop_losses:
                for take_profit in take_profits:
                    test_num += 1
                    
                    # Skip if TP <= SL
                    if take_profit <= stop_loss:
                        logger.warning(f"[{test_num}/{total_tests}] Skipping: TP <= SL")
                        continue
                    
                    config_name = f"pos{pos_size*100:.0f}_sl{stop_loss*100:.1f}_tp{take_profit*100:.0f}"
                    
                    try:
                        await self.test_configuration(
                            position_size=pos_size,
                            stop_loss=stop_loss,
                            take_profit=take_profit,
                            config_name=config_name
                        )
                        
                        logger.info(f"[{test_num}/{total_tests}] Completed: {config_name}")
                        
                    except Exception as e:
                        logger.error(f"[{test_num}/{total_tests}] Failed: {config_name} - {e}")
        
        logger.info("\n[OK] Optimization complete!")
    
    def analyze_results(self):
        """Analyze and rank results."""
        
        if not self.results:
            logger.warning("No results to analyze")
            return
        
        df = pd.DataFrame(self.results)
        
        logger.info("\n" + "="*60)
        logger.info("OPTIMIZATION RESULTS")
        logger.info("="*60)
        
        # Top 5 by Sharpe Ratio
        logger.info("\nTop 5 by Sharpe Ratio:")
        top_sharpe = df.nlargest(5, 'sharpe_ratio')
        for i, row in enumerate(top_sharpe.itertuples(), 1):
            logger.info(f"{i}. {row.config_name}")
            logger.info(f"   Return: {row.total_return:.2f}%, Sharpe: {row.sharpe_ratio:.2f}, "
                       f"DD: {row.max_drawdown_pct:.2f}%, Trades: {row.total_trades}")
        
        # Top 5 by Total Return
        logger.info("\nTop 5 by Total Return:")
        top_return = df.nlargest(5, 'total_return')
        for i, row in enumerate(top_return.itertuples(), 1):
            logger.info(f"{i}. {row.config_name}")
            logger.info(f"   Return: {row.total_return:.2f}%, Sharpe: {row.sharpe_ratio:.2f}, "
                       f"DD: {row.max_drawdown_pct:.2f}%, Trades: {row.total_trades}")
        
        # Best balanced configuration (Sharpe > 1.5, Return > 0, DD < -15%)
        logger.info("\nBest Balanced Configurations:")
        balanced = df[(df['sharpe_ratio'] > 1.5) & 
                     (df['total_return'] > 0) & 
                     (df['max_drawdown_pct'] > -15)]
        
        if len(balanced) > 0:
            balanced = balanced.nlargest(3, 'sharpe_ratio')
            for i, row in enumerate(balanced.itertuples(), 1):
                logger.info(f"{i}. {row.config_name}")
                logger.info(f"   Return: {row.total_return:.2f}%, Sharpe: {row.sharpe_ratio:.2f}, "
                           f"DD: {row.max_drawdown_pct:.2f}%, WinRate: {row.win_rate:.1f}%")
        else:
            logger.warning("   No configurations meet balanced criteria")
        
        # Save results to CSV
        output_dir = Path("backtests/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = output_dir / f"optimization_{self.symbol}_{timestamp}.csv"
        df.to_csv(csv_file, index=False)
        logger.info(f"\n[OK] Results saved to {csv_file}")
        
        # Save best config to JSON
        best_config = df.nlargest(1, 'sharpe_ratio').iloc[0]
        json_file = output_dir / f"best_config_{self.symbol}_{timestamp}.json"
        
        best_params = {
            'symbol': self.symbol,
            'config_name': best_config['config_name'],
            'parameters': {
                'position_size': float(best_config['position_size']),
                'stop_loss': float(best_config['stop_loss']),
                'take_profit': float(best_config['take_profit'])
            },
            'performance': {
                'total_return': float(best_config['total_return']),
                'sharpe_ratio': float(best_config['sharpe_ratio']),
                'sortino_ratio': float(best_config['sortino_ratio']),
                'max_drawdown_pct': float(best_config['max_drawdown_pct']),
                'win_rate': float(best_config['win_rate']),
                'profit_factor': float(best_config['profit_factor'])
            },
            'timestamp': timestamp
        }
        
        with open(json_file, 'w') as f:
            json.dump(best_params, f, indent=2)
        
        logger.info(f"[OK] Best config saved to {json_file}")
        
        # Print best configuration
        logger.info("\n" + "="*60)
        logger.info("RECOMMENDED CONFIGURATION")
        logger.info("="*60)
        logger.info(f"\nSymbol: {self.symbol}")
        logger.info(f"Config: {best_config['config_name']}")
        logger.info(f"\nParameters:")
        logger.info(f"  Position Size: {best_config['position_size']*100:.1f}%")
        logger.info(f"  Stop Loss: {best_config['stop_loss']*100:.2f}%")
        logger.info(f"  Take Profit: {best_config['take_profit']*100:.2f}%")
        logger.info(f"\nExpected Performance:")
        logger.info(f"  Total Return: {best_config['total_return']:.2f}%")
        logger.info(f"  Sharpe Ratio: {best_config['sharpe_ratio']:.2f}")
        logger.info(f"  Win Rate: {best_config['win_rate']:.1f}%")
        logger.info(f"  Max Drawdown: {best_config['max_drawdown_pct']:.2f}%")


async def main():
    """Run parameter optimization."""
    
    # Check for data file - try real data first
    data_file = "BTC-USDTUSDT_15m.csv"
    
    if not Path(f"backtests/data/{data_file}").exists():
        # Fallback to sample data
        data_file = "BTC-USDT_15m_sample.csv"
        if not Path(f"backtests/data/{data_file}").exists():
            logger.error(f"Data file not found: backtests/data/{data_file}")
            logger.info("Please run: python backtests/data_loader.py (to create sample data)")
            logger.info("Or run: python scripts/download_historical_data.py (for real data)")
            return
        logger.info("Using SAMPLE data for optimization")
    
    symbol = "BTC-USDT"
    
    # Create optimizer
    optimizer = ParameterOptimizer(
        data_file=data_file,
        symbol=symbol,
        initial_capital=10000.0
    )
    
    # Run optimization
    await optimizer.run_optimization()
    
    # Analyze results
    optimizer.analyze_results()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("BACKTEST PARAMETER OPTIMIZATION")
    print("="*60 + "\n")
    
    asyncio.run(main())

