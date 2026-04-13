import matplotlib.pyplot as plt
import pandas as pd

def plot_backtest_results(data, trades, symbol):
    """
    Plot backtest results.
    """
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 10))

    # Subplot 1: Price and signals
    ax1.plot(data.index, data['Close'], label='Close Price', color='blue', alpha=0.6)
    
    # Buy/Sell markers
    if not trades.empty:
        buy_trades = trades[trades['Type'] == 'BUY']
        sell_trades = trades[trades['Type'] == 'SELL']
        
        ax1.scatter(buy_trades['Date'], buy_trades['Price'], marker='^', color='green', label='Buy Signal', s=100)
        ax1.scatter(sell_trades['Date'], sell_trades['Price'], marker='v', color='red', label='Sell Signal', s=100)

    ax1.set_title(f'{symbol} Backtest Results - Price & Signals')
    ax1.set_ylabel('Price (TWD)')
    ax1.legend()
    ax1.grid(True)

    # Subplot 2: Equity Curve
    ax2.plot(data.index, data['TotalAssets'], label='Total Assets', color='orange')
    ax2.set_title('Equity Curve (Initial: 1M TWD)')
    ax2.set_ylabel('Asset Value (TWD)')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.show()

def show_summary(performance, trades):
    """
    Print backtest summary performance.
    """
    print("\n--- Backtest Performance Summary ---")
    for key, value in performance.items():
        if 'Return' in key or 'Drawdown' in key:
            print(f"{key}: {value:.2f}%")
        else:
            print(f"{key}: {value:,.0f} TWD")
    
    print(f"Total Number of Trades: {len(trades)}")
    print("------------------------------------\n")
