from data_loader import fetch_stock_data
from strategy import VolumePriceBreakoutStrategy, MACrossoverStrategy
from backtester import Backtester
from visualizer import plot_backtest_results, show_summary
import pandas as pd
import datetime

def run_backtest(symbol, strategy_obj, start_date, end_date):
    """
    Run backtest for a single configuration.
    """
    # 1. Fetch data
    df = fetch_stock_data(symbol, start_date, end_date)
    if df is None:
        return None, None

    print(f"\n===== Starting Backtest: {symbol} =====")
    print(f"Strategy: {strategy_obj.__class__.__name__}")
    
    # 2. Apply strategy
    df_with_signals = strategy_obj.apply(df)

    # 3. Run backtest
    backtester = Backtester(initial_capital=1000000.0)
    result_data, trades = backtester.run(df_with_signals)

    # 4. Calculate performance
    performance = backtester.calculate_performance(result_data)

    # 5. Show summary
    show_summary(performance, trades)

    # 6. Visualization (Optional)
    # plot_backtest_results(result_data, trades, symbol)
    
    return performance, trades

def main():
    # Set backtest period
    start_date = '2023-01-01'
    # Use today's date or a fixed date for consistency
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    
    # Test configurations
    test_configurations = [
        {
            'symbol': '8299', # Phison Electronics
            'strategy': VolumePriceBreakoutStrategy(price_window=20, volume_multiplier=1.5)
        },
        {
            'symbol': '2330', # TSMC
            'strategy': MACrossoverStrategy(fast_ma=5, slow_ma=20)
        },
        {
            'symbol': '2317', # Foxconn
            'strategy': VolumePriceBreakoutStrategy(price_window=20, volume_multiplier=1.5)
        }
    ]

    for config in test_configurations:
        try:
            run_backtest(
                symbol=config['symbol'],
                strategy_obj=config['strategy'],
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            print(f"Error during backtest of {config['symbol']}: {e}")

if __name__ == "__main__":
    main()
