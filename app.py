import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
from data_loader import fetch_stock_data, get_taiwan_50_symbols, get_taiwan_50_info, get_recent_adjustments
from strategy import VolumePriceBreakoutStrategy, MACrossoverStrategy
from backtester import Backtester

# 設定頁面資訊
st.set_page_config(page_title="Large-Cap Stock Monitor", layout="wide", page_icon="🔍")

# --- 1. 定義回呼函數 (Callbacks) ---
# 用於處理右側 Quick Select 點擊跳轉與回測觸發
def handle_nav_click(symbol):
    st.session_state.symbol_input = symbol
    st.session_state.mode_radio = "Individual Backtest"
    st.session_state.trigger_backtest = True

# --- 2. 初始化 Session State ---
if 'mode_radio' not in st.session_state:
    st.session_state.mode_radio = "Signal Scanner (Top 50)"
if 'symbol_input' not in st.session_state:
    st.session_state.symbol_input = "2330"
if 'trigger_backtest' not in st.session_state:
    st.session_state.trigger_backtest = False

# 獲取名稱對照表與變動資訊
tw50_info = get_taiwan_50_info()
recent_adjustments = get_recent_adjustments()

# 主標題
st.title("🔍 Taiwan Stock Signal Scanner & Backtester")

# 使用 columns 建立主畫面與右側導航欄
main_col, nav_col = st.columns([4, 1])

with main_col:
    # 側邊欄：功能模式切換
    st.sidebar.header("Navigation")
    # 元件直接與 key 綁定
    mode = st.sidebar.radio(
        "Choose Mode", 
        ["Signal Scanner (Top 50)", "Individual Backtest"], 
        key="mode_radio"
    )

    # --- 模式說明展示 ---
    if st.session_state.mode_radio == "Signal Scanner (Top 50)":
        with st.expander("📖 Mode Description: Signal Scanner", expanded=True):
            st.info("""
            **掃描儀模式 (Signal Scanner)**:
            - **目的**: 快速篩選出台灣 50 指數成分股中，最近出現進場或出場訊號的股票。
            - **包含範圍**: 目前台灣 50 成分股，以及最近 10 天內新增或移除的股票。
            """)
    else:
        with st.expander("📖 Mode Description: Individual Backtest", expanded=True):
            st.info("""
            **個股回測模式 (Individual Backtest)**:
            - **目的**: 針對單一股票進行深度的策略回測。
            - **功能**: 自定義日期、參數。輸出：資產曲線、買賣點圖表以及交易明細。
            """)

    # --- 核心邏輯 ---
    if st.session_state.mode_radio == "Individual Backtest":
        st.sidebar.divider()
        # 直接與 key 綁定
        symbol = st.sidebar.text_input("Stock Symbol", key="symbol_input")
        
        start_date = st.sidebar.date_input("Start Date", value=datetime.date(2023, 1, 1))
        end_date = st.sidebar.date_input("End Date", value=datetime.date.today())
        
        # 獲取顯示名稱
        current_sym = st.session_state.symbol_input
        stock_name = tw50_info.get(current_sym, recent_adjustments.get(current_sym, {}).get('name', ""))
        display_title = f"{current_sym} {stock_name}" if stock_name else current_sym
        
        strategy_name = st.sidebar.selectbox("Select Strategy", ["Volume Price Breakout", "MA Crossover", "Institutional Trend Following"])
        
        if strategy_name == "Volume Price Breakout":
            with st.expander("💡 Strategy Design: Volume Price Breakout", expanded=True):
                st.success("""
                **量價突破策略邏輯**:
                - **進場**: 價格破 N 日高點且成交量 > M 倍平均成交量。
                - **出場**: 跌破 X 日最低點。
                """)
            pw = st.sidebar.slider("Price High Window (N)", 5, 60, 20)
            vm = st.sidebar.slider("Volume Multiplier (M)", 1.0, 3.0, 1.5, 0.1)
            ew = st.sidebar.slider("Exit Low Window (X)", 3, 30, 10)
            strategy_obj = VolumePriceBreakoutStrategy(price_window=pw, volume_multiplier=vm, exit_window=ew)
        elif strategy_name == "MA Crossover":
            with st.expander("💡 Strategy Design: MA Crossover", expanded=True):
                st.success("""
                **均線交叉策略邏輯**:
                - **進場**: 快線 (5MA) 向上穿過慢線 (20MA)。
                - **出場**: 快線向下穿過慢線。
                """)
            fma = st.sidebar.slider("Fast MA", 5, 20, 5)
            sma = st.sidebar.slider("Slow MA", 20, 120, 20)
            strategy_obj = MACrossoverStrategy(fast_ma=fma, slow_ma=sma)
        else:
            with st.expander("💡 Strategy Design: Institutional Trend Following", expanded=True):
                st.success("""
                **三大法人籌碼策略邏輯**:
                - **進場**: 外資與投信合計買超連續 N 天，且收盤價 > 20MA。
                - **出場**: 法人合計買超轉賣，或股價跌破 20MA。
                """)
            nbd = st.sidebar.slider("Consecutive Net Buy Days", 1, 10, 3)
            maw = st.sidebar.slider("MA Window (Trend)", 5, 60, 20)
            from strategy import InstitutionalStrategy
            strategy_obj = InstitutionalStrategy(net_buy_days=nbd, ma_window=maw)

        # 回測按鈕
        run_backtest_btn = st.sidebar.button("Run Backtest")
        
        if run_backtest_btn or st.session_state.trigger_backtest:
            # 執行後重置標記
            st.session_state.trigger_backtest = False
            
            with st.spinner(f"Running backtest for {display_title}..."):
                df = fetch_stock_data(current_sym, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                if df is not None:
                    df_with_signals = strategy_obj.apply(df)
                    backtester = Backtester()
                    result_data, trades = backtester.run(df_with_signals)
                    perf = backtester.calculate_performance(result_data, trades)
                    
                    st.subheader(f"Results for {display_title}")
                    c1, c2, c3 = st.columns(3)
                    
                    # 報酬率顯示邏輯：如果部位未平倉，顯示 "已實現 (含未實現)"
                    if perf.get('IsOpen', False):
                        return_text = f"{perf['Realized Return (%)']:.2f}% ({perf['Total Return (%)']:.2f}%)"
                        c1.metric("Return (Realized / Total)", return_text)
                    else:
                        c1.metric("Return", f"{perf['Total Return (%)']:.2f}%")
                        
                    c2.metric("MDD", f"{perf['Max Drawdown (%)']:.2f}%")
                    c3.metric("Trades", len(trades))
                    
                    # 視覺化圖表
                    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 10))
                    ax1.plot(result_data.index, result_data['Close'], label='Close Price', color='blue', alpha=0.5)
                    if not trades.empty:
                        buy = trades[trades['Type'] == 'BUY']
                        sell = trades[trades['Type'] == 'SELL']
                        ax1.scatter(buy['Date'], buy['Price'], marker='^', color='green', s=100, label='Buy')
                        ax1.scatter(sell['Date'], sell['Price'], marker='v', color='red', s=100, label='Sell')
                    ax1.set_title(f"Symbol: {current_sym} - Price and Signals")
                    ax1.set_ylabel("Price (TWD)")
                    ax1.legend(); ax1.grid(True, alpha=0.3); ax1.tick_params(labelbottom=True)
                    
                    ax2.plot(result_data.index, result_data['TotalAssets'], color='orange', label='Equity Curve')
                    ax2.fill_between(result_data.index, 1000000.0, result_data['TotalAssets'], color='orange', alpha=0.1)
                    ax2.set_title("Portfolio Equity"); ax2.set_ylabel("Total Assets"); ax2.legend(); ax2.grid(True, alpha=0.3)
                    st.pyplot(fig)
                    
                    if not trades.empty:
                        with st.expander("View Full Trade History"):
                            st.dataframe(trades, use_container_width=True)
                else:
                    st.error("Data fetch failed. Please check symbol.")

    else:
        # --- Scanner Mode ---
        with st.expander("💡 Scanner Strategy: Volume Price Breakout", expanded=True):
            st.info("""
            **目前掃描策略：量價突破 (Volume Price Breakout)**
            - **進場 (Buy)**: 股價創 N 日新高，且成交量達 5 日均量 M 倍。
            - **出場 (Sell)**: 股價跌破 X 日最低點。
            - **掃描範圍**: 尋找在最近幾天內「剛觸發」訊號的股票。
            """)
            
        st.sidebar.divider()
        st.sidebar.subheader("Scanner Settings")
        price_window = st.sidebar.slider("Price High Window (N)", 5, 60, 20)
        vol_mult = st.sidebar.slider("Volume Multiplier (M)", 1.0, 3.0, 1.5, 0.1)
        exit_window = st.sidebar.slider("Exit Low Window (X)", 3, 30, 10)
        scan_days = st.sidebar.slider("Scan Last X Days", 1, 10, 3)
        
        if st.sidebar.button("Scan Taiwan 50"):
            all_symbols = get_taiwan_50_symbols()
            progress_bar = st.progress(0)
            status_text = st.empty()
            found_buy = []; found_sell = []
            
            # 增加抓取天數，確保指標計算正確 (至少要比 price_window 多)
            end_dt = datetime.date.today()
            start_dt = end_dt - datetime.timedelta(days=150)
            strategy_obj = VolumePriceBreakoutStrategy(price_window=price_window, volume_multiplier=vol_mult, exit_window=exit_window)
            
            for i, sym in enumerate(all_symbols):
                name = tw50_info.get(sym, recent_adjustments.get(sym, {}).get('name', "Unknown"))
                status_text.text(f"Scanning {sym} {name} ({i+1}/{len(all_symbols)})")
                progress_bar.progress((i + 1) / len(all_symbols))
                
                df = fetch_stock_data(sym, start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))
                if df is not None and len(df) > max(price_window, exit_window):
                    df_with_signals = strategy_obj.apply(df)
                    
                    # 判定「剛觸發」：今天 Position=1 且 昨天 Position=0
                    df_with_signals['BuyTrigger'] = (df_with_signals['Position'] == 1) & (df_with_signals['Position'].shift(1) == 0)
                    # 判定「剛賣出」：昨天 Position=1 且 今天 Position <= 0
                    df_with_signals['SellTrigger'] = (df_with_signals['Position'] <= 0) & (df_with_signals['Position'].shift(1) == 1)
                    
                    recent = df_with_signals.tail(scan_days)
                    status_tag = recent_adjustments.get(sym, {}).get('type', 'normal')
                    
                    if recent['BuyTrigger'].any():
                        trigger_date = recent[recent['BuyTrigger']].index[-1].strftime('%Y-%m-%d')
                        found_buy.append({'Symbol': sym, 'Name': name, 'Status': status_tag, 'Date': trigger_date, 'Price': f"{df['Close'].iloc[-1]:.2f}", 'Volume': int(df['Volume'].iloc[-1])})
                    if recent['SellTrigger'].any():
                        trigger_date = recent[recent['SellTrigger']].index[-1].strftime('%Y-%m-%d')
                        found_sell.append({'Symbol': sym, 'Name': name, 'Status': status_tag, 'Date': trigger_date, 'Price': f"{df['Close'].iloc[-1]:.2f}", 'Reason': "Broken Support"})
            
            status_text.text("Scan Complete!")
            def style_removed(row):
                color = 'red' if row['Status'] == 'removed' else ''
                return ['color: %s' % color] * len(row)

            st.subheader("🚀 Potential Entry Points (Buy Signals)")
            if found_buy: st.dataframe(pd.DataFrame(found_buy).style.apply(style_removed, axis=1), use_container_width=True)
            else: st.info("No buy signals found.")

            st.subheader("⚠️ Potential Exit Points (Sell Signals)")
            if found_sell: st.dataframe(pd.DataFrame(found_sell).style.apply(style_removed, axis=1), use_container_width=True)
            else: st.info("No sell signals found.")

# --- 右側導航欄：快速跳轉 ---
with nav_col:
    st.subheader("Quick Select (TW50)")
    st.write("Click to Backtest:")
    all_nav_symbols = get_taiwan_50_symbols()
    all_nav_symbols.sort()
    
    for sym in all_nav_symbols:
        name = tw50_info.get(sym, recent_adjustments.get(sym, {}).get('name', "???"))
        adj_type = recent_adjustments.get(sym, {}).get('type', '')
        btn_label = f"{sym} {name}" + (" (Del)" if adj_type == 'removed' else "")
            
        # 使用 on_click 回呼函數安全更新狀態
        st.button(
            btn_label, 
            key=f"nav_{sym}", 
            use_container_width=True, 
            on_click=handle_nav_click, 
            args=(sym,)
        )
