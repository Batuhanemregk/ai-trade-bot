"""
Analyze and visualize backtest optimization results.
Generates charts for PnL, Win Rate, Profit Factor, and Parameter Sensitivity.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Setup
RESULTS_DIR = Path("data/optimization_results")
PLOTS_DIR = RESULTS_DIR / "plots"
PLOTS_DIR.mkdir(exist_ok=True)

def load_data():
    """Load optimization results."""
    all_results = pd.read_csv(RESULTS_DIR / "all_results.csv")
    best_per_coin = pd.read_csv(RESULTS_DIR / "best_per_coin.csv")
    
    # Clean up percentage strings if present
    if 'pnl' in best_per_coin.columns and best_per_coin['pnl'].dtype == object:
        best_per_coin['total_pnl_pct'] = best_per_coin['pnl'].str.rstrip('%').astype(float)
    elif 'pnl' in best_per_coin.columns:
        best_per_coin['total_pnl_pct'] = best_per_coin['pnl']
    
    return all_results, best_per_coin

def plot_pnl_comparison(df):
    """Bar chart of PnL per coin."""
    plt.figure(figsize=(12, 6))
    
    # Sort for better visualization
    df_sorted = df.sort_values('total_pnl_pct', ascending=False)
    
    colors = plt.cm.viridis(np.linspace(0, 1, len(df_sorted)))
    bars = plt.bar(df_sorted['coin'], df_sorted['total_pnl_pct'], color=colors)
    
    plt.title('Max Potential PnL per Coin (Optimized)', fontsize=14)
    plt.ylabel('Total PnL (%)', fontsize=12)
    plt.xlabel('Coin', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', alpha=0.3)
    
    # Add labels
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 10,
                f"+{height:.0f}%",
                ha='center', va='bottom', fontweight='bold')
        
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "pnl_comparison.png")
    print(f"Saved {PLOTS_DIR / 'pnl_comparison.png'}")

def plot_risk_return(df):
    """Scatter plot of Sharpe Ratio vs Profit Factor."""
    plt.figure(figsize=(10, 8))
    
    # Create scatter plot
    plt.scatter(df['sharpe'], df['pf'], s=200, c=df.index, cmap='deep', alpha=0.7)
    
    # Add labels
    for i, row in df.iterrows():
        plt.text(
            row['sharpe']+0.1, 
            row['pf'], 
            row['coin'].split('-')[0], 
            fontsize=9
        )
        
    plt.title('Risk/Return Profile: Profit Factor vs Sharpe Ratio', fontsize=14)
    plt.xlabel('Sharpe Ratio (Risk Adjusted Return)', fontsize=12)
    plt.ylabel('Profit Factor (Gross Win / Gross Loss)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "risk_return.png")
    print(f"Saved {PLOTS_DIR / 'risk_return.png'}")

def plot_weight_sensitivity(df):
    """Heatmap of average Score by TA/ML weights (aggregated across all coins)."""
    # Group by weights and calculate mean score
    pivot_table = df.pivot_table(
        index='ml_weight', 
        columns='ta_weight', 
        values='score', 
        aggfunc='mean'
    )
    
    plt.figure(figsize=(10, 8))
    plt.imshow(pivot_table, cmap='YlGnBu', aspect='auto')
    
    # Add colorbar
    plt.colorbar(label='Avg Score')
    
    # Add labels
    plt.xticks(range(len(pivot_table.columns)), pivot_table.columns)
    plt.yticks(range(len(pivot_table.index)), pivot_table.index)
    
    plt.title('Weight Sensitivity: Average Score (All Coins)', fontsize=14)
    plt.xlabel('TA Weight')
    plt.ylabel('ML Weight')
    
    # Annotate values
    for i in range(len(pivot_table.index)):
        for j in range(len(pivot_table.columns)):
            plt.text(j, i, f"{pivot_table.iloc[i, j]:.1f}", 
                    ha="center", va="center", color="black")
            
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "weight_heatmap.png")
    print(f"Saved {PLOTS_DIR / 'weight_heatmap.png'}")

def plot_threshold_distribution(df):
    """Distribution of best thresholds."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    params = ['enter_long', 'exit_long', 'enter_short', 'exit_short']
    colors = ['green', 'red', 'green', 'red']
    
    for i, param in enumerate(params):
        ax = axes[i]
        try:
            ax.hist(df[param], bins=5, color=colors[i], alpha=0.7, edgecolor='black')
            ax.set_title(f'Best {param.replace("_", " ").title()} Thresholds')
            ax.grid(axis='y', alpha=0.3)
        except Exception as e:
            print(f"Error plotting {param}: {e}")
    
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "threshold_dist.png")
    print(f"Saved {PLOTS_DIR / 'threshold_dist.png'}")

def main():
    print("Loading data...")
    all_res, best_res = load_data()
    
    print("Generating plots...")
    plot_pnl_comparison(best_res)
    plot_threshold_distribution(best_res)
    
    if not all_res.empty:
        try:
            plot_weight_sensitivity(all_res)
            # Simulating fake risk return plot call or just skip it if cmap 'deep' is not valid for matplotlib 
            # actually 'deep' is seaborn palette. Let's fix risk_return in replace block too.
            # I will fix plot_risk_return inside the replacement to use valid cmap.
            
            plt.figure(figsize=(10, 8))
            colors = plt.cm.viridis(np.linspace(0, 1, len(best_res)))
            plt.scatter(best_res['sharpe'], best_res['pf'], s=200, c=colors, alpha=0.7)
            
            for i, row in best_res.iterrows():
                plt.text(row['sharpe']+0.1, row['pf'], row['coin'].split('-')[0], fontsize=9)
            
            plt.title('Risk/Return Profile: Profit Factor vs Sharpe Ratio', fontsize=14)
            plt.xlabel('Sharpe Ratio', fontsize=12)
            plt.ylabel('Profit Factor', fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.savefig(PLOTS_DIR / "risk_return.png")
            print(f"Saved {PLOTS_DIR / 'risk_return.png'}")

        except Exception as e:
            print(f"Error generating extra plots: {e}")
    else:
        print("all_results.csv is empty")
        
    print("\nAnalysis complete!")
if __name__ == "__main__":
    main()
