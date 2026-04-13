import datetime
import pandas as pd
from data_loader import fetch_stock_data, get_taiwan_50_symbols
from strategy import VolumePriceBreakoutStrategy

def run_daily_scan():
    """
    掃描台灣 50 成分股，尋找前一交易日的買賣信號。
    """
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Daily Taiwan 50 Scan...")
    print("Strategy: Volume Price Breakout (Price Window: 20, Vol Multiplier: 1.5)")
    print("-" * 60)

    symbols = get_taiwan_50_symbols()
    
    # 設定策略參數 (可根據您的喜好調整)
    strategy = VolumePriceBreakoutStrategy(price_window=20, volume_multiplier=1.5)
    
    # 設定抓取數據的範圍 (抓最近 60 天確保指標計算正確)
    end_date = datetime.date.today().strftime('%Y-%m-%d')
    start_date = (datetime.date.today() - datetime.timedelta(days=60)).strftime('%Y-%m-%d')

    buy_list = []
    sell_list = []

    for sym in symbols:
        try:
            # 獲取數據
            df = fetch_stock_data(sym, start_date, end_date)
            
            if df is not None and len(df) >= 21:
                # 應用策略
                df_with_signals = strategy.apply(df)
                
                # 檢查最後一天的狀態變化
                # Position: 1 (持有/進場), 0 (空手/出場), -1 (觸發賣出)
                last_row = df_with_signals.iloc[-1]
                prev_row = df_with_signals.iloc[-2]
                
                # 判定買入信號：前一天 Position=0，今天 Position=1
                if prev_row['Position'] == 0 and last_row['Position'] == 1:
                    buy_list.append({
                        'Symbol': sym,
                        'Price': last_row['Close'],
                        'Volume': int(last_row['Volume'])
                    })
                
                # 判定賣出信號：前一天 Position=1，今天 Position=0 (或 -1)
                elif prev_row['Position'] == 1 and last_row['Position'] <= 0:
                    sell_list.append({
                        'Symbol': sym,
                        'Price': last_row['Close'],
                        'Reason': "Price fell below support"
                    })
        except Exception as e:
            # 靜默處理個別股票錯誤，不中斷掃描
            continue

    # 輸出結果
    print("\n🚀 [BUY SIGNALS] - Potential Entry Points:")
    if buy_list:
        for item in buy_list:
            print(f"  + Symbol: {item['Symbol']} | Price: {item['Price']:.2f} | Vol: {item['Volume']:,}")
    else:
        print("  (No buy signals found)")

    print("\n⚠️ [SELL SIGNALS] - Potential Exit Points:")
    if sell_list:
        for item in sell_list:
            print(f"  - Symbol: {item['Symbol']} | Price: {item['Price']:.2f} | {item['Reason']}")
    else:
        print("  (No sell signals found)")

    print("-" * 60)
    print("Scan Completed.")

if __name__ == "__main__":
    run_daily_scan()
