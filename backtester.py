import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, initial_capital=1000000.0, commission=0.001425, tax=0.003):
        """
        Stock market backtesting engine.
        :param initial_capital: Initial capital (TWD)
        :param commission: Trading commission (default 0.1425%)
        :param tax: Transaction tax (default 0.3%, charged when selling)
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.tax = tax

    def run(self, df):
        """
        Execute backtest logic.
        """
        if df is None or df.empty:
            return None, None

        data = df.copy()
        data['Cash'] = self.initial_capital
        data['Holdings'] = 0.0
        data['TotalAssets'] = self.initial_capital
        
        shares_held = 0.0
        cash = self.initial_capital
        trades = []

        # Simulate backtest, executing trades at next day's OPEN price
        for i in range(1, len(data)):
            # Get previous and current position signals
            # Position: 1 for LONG, 0 or -1 for EXIT
            prev_signal = data['Position'].iloc[i-1]
            curr_signal = data['Position'].iloc[i]
            
            open_price = data['Open'].iloc[i]
            
            # Buy signal (0 -> 1)
            if prev_signal == 0 and curr_signal == 1:
                # Calculate max shares (using full capital minus commission)
                # In Taiwan, stocks are traded in lots of 1000, but we support odd lots here
                max_shares = int(cash / (open_price * (1 + self.commission)))
                if max_shares > 0:
                    cost = max_shares * open_price
                    comm_fee = cost * self.commission
                    cash -= (cost + comm_fee)
                    shares_held = max_shares
                    trades.append({
                        'Date': data.index[i],
                        'Type': 'BUY',
                        'Price': open_price,
                        'Shares': max_shares
                    })
            
            # Sell signal (1 -> 0 or 1 -> -1)
            elif prev_signal == 1 and curr_signal <= 0:
                if shares_held > 0:
                    revenue = shares_held * open_price
                    comm_fee = revenue * self.commission
                    tax_fee = revenue * self.tax
                    cash += (revenue - comm_fee - tax_fee)
                    trades.append({
                        'Date': data.index[i],
                        'Type': 'SELL',
                        'Price': open_price,
                        'Shares': shares_held
                    })
                    shares_held = 0.0

            # Update daily account value
            data.loc[data.index[i], 'Cash'] = cash
            data.loc[data.index[i], 'Holdings'] = shares_held * data['Close'].iloc[i]
            data.loc[data.index[i], 'TotalAssets'] = cash + data.loc[data.index[i], 'Holdings']

        return data, pd.DataFrame(trades)

    def calculate_performance(self, data, trades_df):
        """
        Calculate performance metrics.
        """
        # 總報酬率 (包含最後一段未實現的部位)
        total_return = (data['TotalAssets'].iloc[-1] / self.initial_capital) - 1
        
        # 已實現報酬率 (只算到最後一次賣出)
        if not trades_df.empty and (trades_df['Type'].iloc[-1] == 'SELL'):
            realized_return = total_return
            is_open = False
        elif not trades_df.empty and (trades_df['Type'].iloc[-1] == 'BUY'):
            # 如果最後一筆是買入，尋找上一次賣出時的資產
            sell_trades = trades_df[trades_df['Type'] == 'SELL']
            if not sell_trades.empty:
                last_sell_date = sell_trades['Date'].iloc[-1]
                # 找到賣出當天的總資產
                realized_assets = data.loc[last_sell_date, 'TotalAssets']
                if isinstance(realized_assets, pd.Series):
                    realized_assets = realized_assets.iloc[-1]
                realized_return = (realized_assets / self.initial_capital) - 1
            else:
                # 從來沒有賣出過
                realized_return = 0.0
            is_open = True
        else:
            realized_return = total_return
            is_open = False

        # Max Drawdown (MDD)
        equity = data['TotalAssets']
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'Total Return (%)': total_return * 100,
            'Realized Return (%)': realized_return * 100,
            'Max Drawdown (%)': max_drawdown * 100,
            'Ending Capital': data['TotalAssets'].iloc[-1],
            'IsOpen': is_open
        }
