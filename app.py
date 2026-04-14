import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from data_loader import fetch_stock_data, get_taiwan_50_symbols, get_taiwan_50_info
from strategy import VolumePriceBreakoutStrategy, MACrossoverStrategy
from backtester import Backtester

# 設定頁面資訊
st.set_page_config(page_title="Large-Cap Signal Scanner", layout="wide", page_icon="🔍")

# 獲取名稱對照表
tw50_info = get_taiwan_50_info()

st.title("🔍 Taiwan Large-Cap Stock Signal Scanner")
st.markdown("Scan top 50 large-cap stocks for recent trading signals.")

# 側邊欄：功能模式切換
st.sidebar.header("Mode Selection")
mode = st.sidebar.radio("Choose Mode", ["Signal Scanner (Top 50)", "Individual Backtest"])

if mode == "Individual Backtest":
    st.sidebar.divider()
    symbol = st.sidebar.text_input("Stock Symbol", value="2330")
    start_date = st.sidebar.date_input("Start Date", value=datetime.date(2023, 1, 1))
    end_date = st.sidebar.date_input("End Date", value=datetime.date.today())
    
    # 獲取顯示名稱 (用於 UI)
    stock_name = tw50_info.get(symbol, "")
    display_title = f"{symbol} {stock_name}" if stock_name else symbol
    
    strategy_name = st.sidebar.selectbox("Select Strategy", ["Volume Price Breakout", "MA Crossover"])
    if strategy_name == "Volume Price Breakout":
        pw = st.sidebar.slider("Price High Window", 5, 60, 20)
        vm = st.sidebar.slider("Volume Multiplier", 1.0, 3.0, 1.5, 0.1)
        strategy_obj = VolumePriceBreakoutStrategy(price_window=pw, volume_multiplier=vm)
    else:
        fma = st.sidebar.slider("Fast MA", 5, 20, 5)
        sma = st.sidebar.slider("Slow MA", 20, 120, 20)
        strategy_obj = MACrossoverStrategy(fast_ma=fma, slow_ma=sma)

    if st.sidebar.button("Run Backtest"):
        with st.spinner("Processing..."):
            df = fetch_stock_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            if df is not None:
                df_with_signals = strategy_obj.apply(df)
                backtester = Backtester()
                result_data, trades = backtester.run(df_with_signals)
                perf = backtester.calculate_performance(result_data)
                
                # UI 標題可以使用中文
                st.subheader(f"Results for {display_title}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Return", f"{perf['Total Return (%)']:.2f}%")
                c2.metric("MDD", f"{perf['Max Drawdown (%)']:.2f}%")
                c3.metric("Trades", len(trades))
                
                # 視覺化圖表 - 內部標題避免使用中文以防崩潰
                fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 10))
                
                # 子圖 1: 價格與信號
                ax1.plot(result_data.index, result_data['Close'], label='Close Price', color='blue', alpha=0.5)
                if not trades.empty:
                    buy = trades[trades['Type'] == 'BUY']
                    sell = trades[trades['Type'] == 'SELL']
                    ax1.scatter(buy['Date'], buy['Price'], marker='^', color='green', s=100, label='Buy')
                    ax1.scatter(sell['Date'], sell['Price'], marker='v', color='red', s=100, label='Sell')
                
                # 圖表內部標題僅使用代碼
                ax1.set_title(f"Symbol: {symbol} - Price and Signals")
                ax1.set_ylabel("Price (TWD)")
                ax1.legend()
                ax1.grid(True, alpha=0.3)
                ax1.tick_params(labelbottom=True)
                
                # 子圖 2: 資產曲線
                ax2.plot(result_data.index, result_data['TotalAssets'], color='orange', label='Equity Curve')
                ax2.fill_between(result_data.index, 1000000.0, result_data['TotalAssets'], color='orange', alpha=0.1)
                ax2.set_title("Portfolio Equity")
                ax2.set_ylabel("Total Assets")
                ax2.legend()
                ax2.grid(True, alpha=0.3)
                
                st.pyplot(fig)

                # 交易明細清單
                if not trades.empty:
                    with st.expander("View Full Trade History"):
                        st.dataframe(trades, use_container_width=True)
                else:
                    st.warning("No trades were executed with these parameters.")

else:
    # 掃描大型股模式
    st.sidebar.divider()
    st.sidebar.subheader("Scanner Settings")
    price_window = st.sidebar.slider("Price Window (for Breakout)", 5, 60, 20)
    vol_mult = st.sidebar.slider("Volume Multiplier", 1.0, 3.0, 1.5, 0.1)
    scan_days = st.sidebar.slider("Scan Last X Days for Signals", 1, 10, 3)
    
    if st.sidebar.button("Scan Top 50 Stocks"):
        tw50_symbols = get_taiwan_50_symbols()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        found_signals = []
        
        end_dt = datetime.date.today()
        start_dt = end_dt - datetime.timedelta(days=100)
        
        strategy_obj = VolumePriceBreakoutStrategy(price_window=price_window, volume_multiplier=vol_mult)
        
        for i, sym in enumerate(tw50_symbols):
            status_text.text(f"Scanning {sym} {tw50_info.get(sym, '')} ({i+1}/{len(tw50_symbols)})")
            progress_bar.progress((i + 1) / len(tw50_symbols))
            
            df = fetch_stock_data(sym, start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))
            
            if df is not None and len(df) > price_window:
                df_with_signals = strategy_obj.apply(df)
                df_with_signals['BuySignal_Daily'] = (df_with_signals['Position'] == 1) & (df_with_signals['Position'].shift(1) == 0)
                
                recent_signals = df_with_signals.tail(scan_days)
                if recent_signals['BuySignal_Daily'].any():
                    signal_dates = recent_signals[recent_signals['BuySignal_Daily']].index.strftime('%Y-%m-%d').tolist()
                    current_price = df['Close'].iloc[-1]
                    found_signals.append({
                        'Symbol': sym,
                        'Name': tw50_info.get(sym, "Unknown"),
                        'Signal Date(s)': ", ".join(signal_dates),
                        'Current Price': f"{current_price:.2f}",
                        'Last Volume': int(df['Volume'].iloc[-1])
                    })
        
        status_text.text("Scan Complete!")
        
        if found_signals:
            st.success(f"Found {len(found_signals)} stocks with recent breakout signals!")
            st.table(pd.DataFrame(found_signals))
            st.info("You can switch to 'Individual Backtest' mode to see the detailed chart for these symbols.")
        else:
            st.warning("No breakout signals found in the top 50 stocks for the selected criteria.")
