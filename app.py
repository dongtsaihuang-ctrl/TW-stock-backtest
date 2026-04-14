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
# 回呼函數會在腳本重新執行前執行，避免 StreamlitAPIException
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
    # 元件直接綁定 key
    mode = st.sidebar.radio(
        "Choose Mode", 
        ["Signal Scanner (Top 50)", "Individual Backtest"], 
        key="mode_radio"
    )

    # --- 模式說明展示 ---
    if st.session_state.mode_radio == "Signal Scanner (Top 50)":
        with st.expander("📖 Mode Description: Signal Scanner", expanded=True):
            st.info("**掃描儀模式 (Signal Scanner)**: 快速篩選台灣 50 最近出現進場或出場訊號的股票。")
    else:
        with st.expander("📖 Mode Description: Individual Backtest", expanded=True):
            st.info("**個股回測模式 (Individual Backtest)**: 針對單一股票進行深度策略回測與圖表分析。")

    # --- 核心邏輯 ---
    if st.session_state.mode_radio == "Individual Backtest":
        st.sidebar.divider()
        # 元件直接綁定 key
        symbol = st.sidebar.text_input("Stock Symbol", key="symbol_input")
        
        start_date = st.sidebar.date_input("Start Date", value=datetime.date(2023, 1, 1))
        end_date = st.sidebar.date_input("End Date", value=datetime.date.today())
        
        current_sym = st.session_state.symbol_input
        stock_name = tw50_info.get(current_sym, recent_adjustments.get(current_sym, {}).get('name', ""))
        display_title = f"{current_sym} {stock_name}" if stock_name else current_sym
        
        strategy_name = st.sidebar.selectbox("Select Strategy", ["Volume Price Breakout", "MA Crossover"])
        
        if strategy_name == "Volume Price Breakout":
            with st.expander("💡 Strategy Design: Volume Price Breakout", expanded=True):
                st.success("**量價突破**: 價格破20日高 + 成交量 > 1.5倍均量。出場：跌破10日低。")
            pw = st.sidebar.slider("Price High Window", 5, 60, 20)
            vm = st.sidebar.slider("Volume Multiplier", 1.0, 3.0, 1.5, 0.1)
            strategy_obj = VolumePriceBreakoutStrategy(price_window=pw, volume_multiplier=vm)
        else:
            with st.expander("💡 Strategy Design: MA Crossover", expanded=True):
                st.success("**均線交叉**: 快線(5MA)向上穿過慢線(20MA)進場，反之出場。")
            fma = st.sidebar.slider("Fast MA", 5, 20, 5)
            sma = st.sidebar.slider("Slow MA", 20, 120, 20)
            strategy_obj = MACrossoverStrategy(fast_ma=fma, slow_ma=sma)

        # 檢查是否觸發回測
        run_backtest_btn = st.sidebar.button("Run Backtest")
        
        if run_backtest_btn or st.session_state.trigger_backtest:
            st.session_state.trigger_backtest = False
            with st.spinner(f"Processing {display_title}..."):
                df = fetch_stock_data(current_sym, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                if df is not None:
                    df_with_signals = strategy_obj.apply(df)
                    backtester = Backtester()
                    result_data, trades = backtester.run(df_with_signals)
                    perf = backtester.calculate_performance(result_data)
                    
                    st.subheader(f"Results for {display_title}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Return", f"{perf['Total Return (%)']:.2f}%")
                    c2.metric("MDD", f"{perf['Max Drawdown (%)']:.2f}%")
                    c3.metric("Trades", len(trades))
                    
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
        # --- Scanner Mode ---
        st.sidebar.divider()
        st.sidebar.subheader("Scanner Settings")
        price_window = st.sidebar.slider("Price Window", 5, 60, 20)
        vol_mult = st.sidebar.slider("Volume Multiplier", 1.0, 3.0, 1.5, 0.1)
        scan_days = st.sidebar.slider("Scan Last X Days", 1, 10, 3)
        
        if st.sidebar.button("Scan Taiwan 50 (Incl. Adjustments)"):
            all_symbols = get_taiwan_50_symbols()
            progress_bar = st.progress(0)
            status_text = st.empty()
            found_buy = []; found_sell = []
            
            end_dt = datetime.date.today()
            start_dt = end_dt - datetime.timedelta(days=100)
            strategy_obj = VolumePriceBreakoutStrategy(price_window=price_window, volume_multiplier=vol_mult)
            
            for i, sym in enumerate(all_symbols):
                name = tw50_info.get(sym, recent_adjustments.get(sym, {}).get('name', "Unknown"))
                status_text.text(f"Scanning {sym} {name} ({i+1}/{len(all_symbols)})")
                progress_bar.progress((i + 1) / len(all_symbols))
                
                df = fetch_stock_data(sym, start_dt.strftime('%Y-%m-%d'), end_dt.strftime('%Y-%m-%d'))
                if df is not None and len(df) > price_window:
                    df_with_signals = strategy_obj.apply(df)
                    df_with_signals['BuySignal'] = (df_with_signals['Position'] == 1) & (df_with_signals['Position'].shift(1) == 0)
                    df_with_signals['SellSignal'] = (df_with_signals['Position'] <= 0) & (df_with_signals['Position'].shift(1) == 1)
                    recent = df_with_signals.tail(scan_days)
                    
                    status_tag = recent_adjustments.get(sym, {}).get('type', 'normal')
                    if recent['BuySignal'].any():
                        found_buy.append({'Symbol': sym, 'Name': name, 'Status': status_tag, 'Date': ", ".join(recent[recent['BuySignal']].index.strftime('%Y-%m-%d')), 'Price': f"{df['Close'].iloc[-1]:.2f}", 'Volume': int(df['Volume'].iloc[-1])})
                    if recent['SellSignal'].any():
                        found_sell.append({'Symbol': sym, 'Name': name, 'Status': status_tag, 'Date': ", ".join(recent[recent['SellSignal']].index.strftime('%Y-%m-%d')), 'Price': f"{df['Close'].iloc[-1]:.2f}", 'Volume': int(df['Volume'].iloc[-1])})
            
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
            
        # 關鍵：使用 on_click 回呼函數，避免在渲染後修改狀態
        st.button(
            btn_label, 
            key=f"nav_{sym}", 
            use_container_width=True, 
            on_click=handle_nav_click, 
            args=(sym,)
        )
