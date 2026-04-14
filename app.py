import streamlit as st
import pandas as pd
import datetime
from data_loader import fetch_stock_data, get_taiwan_50_symbols, get_taiwan_50_info

# ... (保持原有的 import)

# 在這裡獲取名稱對照表
tw50_info = get_taiwan_50_info()

# ... (保持原有的 mode 選擇邏輯)

if mode == "Individual Backtest":
    # ...
    # 獲取顯示名稱
    stock_name = tw50_info.get(symbol, "")
    display_title = f"{symbol} {stock_name}" if stock_name else symbol
    
    if st.sidebar.button("Run Backtest"):
        with st.spinner("Processing..."):
            df = fetch_stock_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            if df is not None:
                # ... (保持運算邏輯)
                st.subheader(f"Results for {display_title}")
                # ... (保持 metric 顯示)
                
                # 視覺化圖表 (修改：強制顯示兩張圖的日期)
                import matplotlib.pyplot as plt
                fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 10))
                
                # 子圖 1: 價格與信號
                ax1.plot(result_data.index, result_data['Close'], label='Close Price', color='blue', alpha=0.5)
                # ... (標註買賣點)
                ax1.set_title(f"{display_title} Price and Trading Signals")
                ax1.set_ylabel("Price (TWD)")
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                # 強制顯示第一張圖的日期標籤 (原本被 sharex 隱藏)
                ax1.tick_params(labelbottom=True)
                
                # 子圖 2: 資產曲線
                # ... (代碼與原本相同)
                st.pyplot(fig)
# ...
else:
    # Scan Mode
    # ...
    if st.sidebar.button("Scan Top 50 Stocks"):
        # ...
        for i, sym in enumerate(tw50_symbols):
            # ...
            if recent_signals['BuySignal_Daily'].any():
                # ...
                found_signals.append({
                    'Symbol': sym,
                    'Name': tw50_info.get(sym, "Unknown"), # 新增名稱欄位
                    'Signal Date(s)': ", ".join(signal_dates),
                    'Current Price': f"{current_price:.2f}",
                    'Last Volume': int(df['Volume'].iloc[-1])
                })
        
        status_text.text("Scan Complete!")
        
        if found_signals:
            st.success(f"Found {len(found_signals)} stocks with recent breakout signals!")
            st.table(pd.DataFrame(found_signals))
            st.info("You can switch to 'Individual Backtest' mode to see the detailed chart for these stocks.")
        else:
            st.warning("No breakout signals found in the top 50 stocks for the selected criteria.")
