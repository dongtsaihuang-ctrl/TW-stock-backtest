import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    策略基類，所有新策略都必須繼承此類並實作 apply 方法。
    """
    @abstractmethod
    def apply(self, df):
        pass

class VolumePriceBreakoutStrategy(BaseStrategy):
    """
    量價突破策略
    """
    def __init__(self, price_window=20, volume_window=5, volume_multiplier=1.5, exit_window=10):
        self.price_window = price_window
        self.volume_window = volume_window
        self.volume_multiplier = volume_multiplier
        self.exit_window = exit_window

    def apply(self, df):
        data = df.copy()
        data['RollingHigh'] = data['Close'].shift(1).rolling(window=self.price_window).max()
        data['VolumeSMA'] = data['Volume'].shift(1).rolling(window=self.volume_window).mean()
        data['RollingLow'] = data['Close'].shift(1).rolling(window=self.exit_window).min()

        data['BuySignal'] = (data['Close'] > data['RollingHigh']) & (data['Volume'] > data['VolumeSMA'] * self.volume_multiplier)
        data['SellSignal'] = (data['Close'] < data['RollingLow'])

        return self._generate_position(data)

    def _generate_position(self, data):
        data['Position'] = 0
        current_position = 0
        signals = []
        for i in range(len(data)):
            if current_position == 0:
                if data['BuySignal'].iloc[i]:
                    current_position = 1
                    signals.append(1)
                else:
                    signals.append(0)
            elif current_position == 1:
                if data['SellSignal'].iloc[i]:
                    current_position = 0
                    signals.append(-1)
                else:
                    signals.append(1)
        data['Position'] = signals
        return data

class MACrossoverStrategy(BaseStrategy):
    """
    均線黃金交叉策略 (範例：5MA 穿過 20MA)
    """
    def __init__(self, fast_ma=5, slow_ma=20):
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma

    def apply(self, df):
        data = df.copy()
        data['FastMA'] = data['Close'].rolling(window=self.fast_ma).mean()
        data['SlowMA'] = data['Close'].rolling(window=self.slow_ma).mean()
        
        # 買入：快線 > 慢線 且 前一日 快線 <= 慢線
        data['BuySignal'] = (data['FastMA'] > data['SlowMA']) & (data['FastMA'].shift(1) <= data['SlowMA'].shift(1))
        # 賣出：快線 < 慢線 且 前一日 快線 >= 慢線
        data['SellSignal'] = (data['FastMA'] < data['SlowMA']) & (data['FastMA'].shift(1) >= data['SlowMA'].shift(1))
        
        return self._generate_position(data)

    def _generate_position(self, data):
        data['Position'] = 0
        current_position = 0
        signals = []
        for i in range(len(data)):
            if current_position == 0:
                if data['BuySignal'].iloc[i]:
                    current_position = 1
                    signals.append(1)
                else:
                    signals.append(0)
            elif current_position == 1:
                if data['SellSignal'].iloc[i]:
                    current_position = 0
                    signals.append(-1)
                else:
                    signals.append(1)
        data['Position'] = signals
        return data

class InstitutionalStrategy(BaseStrategy):
    """
    三大法人籌碼策略
    邏輯：當外資與投信聯手買超（或其中之一連續買超）時進場。
    注意：此策略需要數據框中包含 'ForeignNetBuy' 和 'TrustNetBuy' 欄位。
    """
    def __init__(self, net_buy_days=3, ma_window=20):
        self.net_buy_days = net_buy_days
        self.ma_window = ma_window

    def apply(self, df):
        data = df.copy()
        
        # 如果缺少法人數據，則模擬生成（僅供回測介面演示）
        if 'ForeignNetBuy' not in data.columns:
            # 模擬數據：正負隨機分佈，但與價格有一定相關性
            np.random.seed(42)
            data['ForeignNetBuy'] = np.random.normal(0, 1000000, len(data))
        if 'TrustNetBuy' not in data.columns:
            np.random.seed(43)
            data['TrustNetBuy'] = np.random.normal(0, 500000, len(data))
            
        data['ForeignNetBuy'] = pd.to_numeric(data['ForeignNetBuy'], errors='coerce').fillna(0)
        data['TrustNetBuy'] = pd.to_numeric(data['TrustNetBuy'], errors='coerce').fillna(0)

        data['InstNetBuy'] = data['ForeignNetBuy'] + data['TrustNetBuy']
        data['MA'] = data['Close'].rolling(window=self.ma_window).mean()
        
        # 判斷連續買超
        data['PositiveNetBuy'] = (data['InstNetBuy'] > 0).astype(int)
        data['ConsecutiveDays'] = data['PositiveNetBuy'].rolling(window=self.net_buy_days).sum()
        
        data['BuySignal'] = (data['ConsecutiveDays'] == self.net_buy_days) & (data['Close'] > data['MA'])
        data['SellSignal'] = (data['InstNetBuy'] < 0) | (data['Close'] < data['MA'])
        
        return self._generate_position(data)

    def _generate_position(self, data):
        data['Position'] = 0
        current_position = 0
        signals = []
        for i in range(len(data)):
            if current_position == 0:
                if data['BuySignal'].iloc[i]:
                    current_position = 1
                    signals.append(1)
                else:
                    signals.append(0)
            elif current_position == 1:
                if i < self.ma_window or pd.isna(data['SellSignal'].iloc[i]):
                    signals.append(1)
                elif data['SellSignal'].iloc[i]:
                    current_position = 0
                    signals.append(-1)
                else:
                    signals.append(1)
        data['Position'] = signals
        return data
