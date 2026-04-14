import yfinance as yf
import pandas as pd
import sys
import contextlib
import os

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
    
    # 在 Streamlit 環境下，print 會輸出到後台 log
    # 這裡我們移除掉可能會導致編碼衝突的複雜 print
    
    for s in symbols_to_try:
        try:
            with suppress_stdout_stderr():
                df = yf.download(s, start=start_date, end=end_date, progress=False)
            
            if df is not None and not df.empty:
                data = df
                break
        except Exception:
            continue
            
    if data is None or data.empty:
        return None
    
    # Flatten MultiIndex columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
        
    return data[['Open', 'High', 'Low', 'Close', 'Volume']]

def get_taiwan_50_info():
    """
    Returns a dictionary of Taiwan Top 50 symbols and their Chinese names.
    """
    return {
        '2330': '台積電', '2317': '鴻海', '2454': '聯發科', '2308': '台達電', '2303': '聯電',
        '2881': '富邦金', '2882': '國泰金', '2382': '廣達', '2891': '中信金', '3711': '日月光投控',
        '2412': '中華電', '2886': '兆豐金', '1301': '台塑', '1303': '南亞', '2884': '玉山金',
        '1216': '統一', '2892': '第一金', '2885': '元大金', '2002': '中鋼', '3008': '大立光',
        '2357': '華碩', '2880': '華南金', '2327': '國巨', '5880': '合庫金', '2890': '永豐金',
        '2603': '長榮', '1326': '台化', '2379': '瑞昱', '6669': '緯穎', '2883': '開發金',
        '2912': '統一超', '1101': '台泥', '3034': '聯詠', '3045': '台灣大', '2395': '研華',
        '2408': '南亞科', '5876': '上海商銀', '1590': '亞德客-KY', '4966': '譜瑞-KY', '2609': '陽明',
        '2615': '萬海', '2474': '可成', '2377': '微星', '2301': '光寶科', '3231': '緯創',
        '2887': '台新金', '4938': '和碩', '6505': '台塑化', '9904': '寶成', '2409': '友達'
    }

def get_taiwan_50_symbols():
    """
    Returns a list of symbols for Taiwan Top 50.
    """
    return list(get_taiwan_50_info().keys())
