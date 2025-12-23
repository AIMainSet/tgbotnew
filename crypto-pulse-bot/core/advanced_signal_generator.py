import pandas as pd
import pandas_ta as ta
import ccxt.async_support as ccxt
import asyncio
import logging
from config import config


class AdvancedSignalGenerator:
    def __init__(self):
        self.exchange = getattr(ccxt, 'bybit')({
            'enableRateLimit': True,
            'apiKey': config.BYBIT_API_KEY,
            'secret': config.BYBIT_API_SECRET,
        })
        # ВАЖНО: Тестнет Bybit иногда нестабилен. Для реальных данных позже уберем.
        self.exchange.set_sandbox_mode(True)
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

    async def get_data_and_analyze(self, symbol: str):
        try:
            ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            if not ohlcv or len(ohlcv) < 20:
                return None

            df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])

            # Индикаторы
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['ema_20'] = ta.ema(df['close'], length=20)
            df['ema_50'] = ta.ema(df['close'], length=50)

            last = df.iloc[-1]
            prev = df.iloc[-2]  # Теперь мы её используем!

            direction = None

            # ЛОГИКА BUY:
            # 1. RSI ниже 40 (перепроданность)
            # 2. EMA20 выше EMA50 (бычий тренд)
            # 3. ЦЕНА закрылась ВЫШЕ EMA20 (подтверждение разворота)
            if 10 < last['rsi'] < 40 and last['ema_20'] > last['ema_50']:
                if prev['close'] <= prev['ema_20']:  # Используем prev: цена пересекла среднюю снизу вверх
                    direction = "buy"

            # ЛОГИКА SELL:
            elif 60 < last['rsi'] < 90 and last['ema_20'] < last['ema_50']:
                if prev['close'] >= prev['ema_20']:  # Используем prev: цена пересекла среднюю сверху вниз
                    direction = "sell"

            if direction:
                # Сделаем Risk/Reward Ratio 1:2 (Стоп 1.5%, Тейк 3%)
                tp_mult = 1.03 if direction == "buy" else 0.97
                sl_mult = 0.985 if direction == "buy" else 1.015

                return {
                    'symbol': symbol,
                    'side': direction,
                    'entry': float(last['close']),
                    'tp': float(last['close'] * tp_mult),
                    'sl': float(last['close'] * sl_mult),
                    'timeframe': '1h',
                    'reason': f"RSI:{round(last['rsi'], 1)} + EMA Cross Confirmation"
                }
        except Exception as e:
            logging.error(f"Ошибка анализа {symbol}: {e}")
        return None

    async def run_analysis_cycle(self):
        signals = []
        for symbol in self.symbols:
            sig = await self.get_data_and_analyze(symbol)
            if sig:
                signals.append(sig)
            await asyncio.sleep(0.2)  # Небольшая пауза, чтобы не спамить API
        return signals

    async def close(self):
        """Метод для корректного завершения работы"""
        await self.exchange.close()