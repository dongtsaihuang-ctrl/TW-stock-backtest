import yfinance as yf
import pandas as pd
import sys
import contextlib
import os

# Ensure output encoding is UTF-8 if possible
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

def format_taiwan_symbol(symbol):
    """
    Format Taiwan stock symbols for yfinance.
    TSEC stocks use .TW, OTC stocks use .TWO.
    """
    symbol = str(symbol).strip().upper()
    
    if symbol.endswith('.TW') or symbol.endswith('.TWO'):
        return [symbol]
    
    if symbol.isdigit():
        # Try both suffixes if it's just a number
        return [f"{symbol}.TW", f"{symbol}.TWO"]
    
    return [symbol]

@contextlib.contextmanager
def suppress_stdout_stderr():
    """Context manager to suppress stdout and stderr."""
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

def fetch_stock_data(symbol, start_date, end_date):
    """
    Fetch historical stock data from Yahoo Finance.
    Automatically handles Taiwan stock suffixes.
    """
    symbols_to_try = format_taiwan_symbol(symbol)
    
    data = None
    actual_symbol = None
    
    print(f"Searching for symbol: {symbol} (Try: {symbols_to_try})")
    
    for s in symbols_to_try:
        try:
            # Use suppress_stdout_stderr to hide yfinance noise
            with suppress_stdout_stderr():
                df = yf.download(s, start=start_date, end=end_date, progress=False)
            
            if df is not None and not df.empty:
                data = df
                actual_symbol = s
                print(f"Successfully fetched data for: {s}")
                break
        except Exception as e:
            continue
            
    if data is None or data.empty:
        print(f"Error: Could not fetch data for {symbol}. Please check the symbol.")
        return None
    
    # Flatten MultiIndex columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    return data[['Open', 'High', 'Low', 'Close', 'Volume']]

def get_taiwan_50_symbols():
    """
    Returns a list of symbols for Taiwan Top 50 index (0050 components).
    Note: In a production environment, this should be fetched from a live source.
    Here we use a pre-defined list for reliability.
    """
    # Standard Taiwan 50 components (approximate, common large caps)
    return [
        '2330', '2317', '2454', '2308', '2303', '2881', '2882', '2382', '2891', '3711',
        '2412', '2886', '1301', '1303', '2884', '1216', '2892', '2885', '2002', '3008',
        '2357', '2880', '2327', '5880', '2890', '2603', '1326', '2379', '6669', '2883',
        '2912', '1101', '3034', '3045', '2395', '2408', '5876', '1590', '4966', '2609',
        '2615', '2474', '2377', '2301', '3231', '2887', '4938', '6505', '9904', '2409'
    ]

if __name__ == "__main__":
    df = fetch_stock_data('8299', '2023-01-01', '2024-01-01')
    if df is not None:
        print(df.head())
