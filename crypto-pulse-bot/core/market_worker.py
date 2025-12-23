import asyncio
import logging
import os
from sqlalchemy import select
from aiogram import Bot
from aiogram.types import FSInputFile

# Твои внутренние модули
from core.advanced_signal_generator import AdvancedSignalGenerator
from analytics.signal_tracker import SignalTracker
from database import async_session, User, check_and_expire_subscriptions
from core.chart_gen import create_signal_chart


# Вспомогательная функция расчета объема позиции
def calculate_position_size(deposit, risk_pct, entry, sl):
    try:
        if not deposit or not risk_pct or deposit <= 0 or risk_pct <= 0:
            return 0
        risk_amount = deposit * (risk_pct / 100)
        stop_distance = abs(entry - sl) / entry
        if stop_distance <= 0:
            return 0
        # Объем позиции в USDT
        position_size_usdt = risk_amount / stop_distance
        return round(position_size_usdt, 2)
    except Exception:
        return 0


class MarketWorker:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.gen = AdvancedSignalGenerator()
        self.tracker = SignalTracker(bot)

    async def start(self):
        """Запуск всех фоновых задач воркера"""
        # 1. Запуск мониторинга открытых сделок (для TP/SL)
        asyncio.create_task(self.tracker.start_monitoring(self.gen.exchange))

        # 2. Запуск проверки истечения подписок
        asyncio.create_task(self.subscription_checker())

        logging.info("🕵️ Воркер анализа рынка запущен (Мониторинг + Графики)...")

        # 3. Основной цикл поиска сигналов
        while True:
            try:
                # Получаем список новых сигналов от генератора
                new_sigs = await self.gen.run_analysis_cycle()

                if new_sigs:
                    for s in new_sigs:
                        # Добавляем в трекер для слежения за ценой
                        await self.tracker.add_signal(s)
                        # Рассылаем пользователям с графиком и расчетом риска
                        await self.broadcast_signal(s)

            except Exception as e:
                logging.error(f"❌ Ошибка в основном цикле воркера: {e}")
                await asyncio.sleep(60)
                continue

            # Интервал между сканированиями рынка (5 минут)
            await asyncio.sleep(300)

    async def subscription_checker(self):
        """Проверка просроченных подписок раз в час"""
        while True:
            try:
                logging.info("⏳ Проверка истекших подписок...")
                expired_user_ids = await check_and_expire_subscriptions()

                for user_id in expired_user_ids:
                    try:
                        await self.bot.send_message(
                            user_id,
                            "⚠️ **Срок действия вашей PREMIUM подписки истек.**\n\n"
                            "Доступ к сигналам ограничен. Чтобы продолжить получать "
                            "точные точки входа, продлите подписку в меню 💎 Подписка."
                        )
                    except Exception as e:
                        logging.error(f"Не удалось уведомить юзера {user_id}: {e}")
            except Exception as e:
                logging.error(f"Ошибка в subscription_checker: {e}")
            await asyncio.sleep(3600)

    async def broadcast_signal(self, signal):
        """Генерация графика и рассылка сигнала подписчикам"""
        symbol = signal['symbol']

        # 1. Получаем свежие данные для графика перед отправкой
        try:
            # Используем биржу из генератора для получения OHLCV
            ohlcv = await self.gen.exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            import pandas as pd
            import pandas_ta as ta

            df = pd.DataFrame(ohlcv, columns=['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume'])
            df['ema_50'] = ta.ema(df['Close'], length=50)
            df['ema_200'] = ta.ema(df['Close'], length=200)

            # Создаем картинку
            chart_path = create_signal_chart(
                df=df,
                symbol=symbol,
                entry=signal['entry'],
                tp=signal['tp'],
                sl=signal['sl'],
                side=signal['side']
            )
        except Exception as e:
            logging.error(f"📈 Ошибка генерации графика для {symbol}: {e}")
            chart_path = None

        # 2. Рассылка по базе данных
        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.status == "PREMIUM")
            )
            users = result.scalars().all()

            for user in users:
                user_pairs = user.selected_pairs.split(",") if user.selected_pairs else []

                # Отправляем только если пара в списке пользователя
                if symbol in user_pairs:
                    pos_size = calculate_position_size(
                        user.deposit,
                        user.risk_per_trade,
                        signal['entry'],
                        signal['sl']
                    )

                    side_emoji = "🟢 LONG" if signal['side'].upper() == "BUY" else "🔴 SHORT"

                    text = (
                        f"🚀 **НОВЫЙ СИГНАЛ: #{symbol.replace('/', '')}**\n"
                        f"────────────────────\n"
                        f"📈 **Тип:** `{side_emoji}`\n"
                        f"📥 **Вход:** `{signal['entry']}`\n"
                        f"🎯 **Тейк-профит:** `{signal['tp']}`\n"
                        f"🛡 **Стоп-лосс:** `{signal['sl']}`\n\n"
                        f"📝 **Анализ:** {signal['reason']}\n"
                        f"────────────────────\n"
                        f"💰 **Ваш риск-менеджмент:**\n"
                        f"▫️ Риск: `{user.risk_per_trade}%` | Депо: `${user.deposit}`\n"
                        f"👉 **Объем сделки:** `${pos_size}`\n"
                        f"────────────────────\n"
                        f"🕒 _Таймфрейм: H1 | Биржа: Bybit_"
                    )

                    try:
                        if chart_path and os.path.exists(chart_path):
                            photo = FSInputFile(chart_path)
                            await self.bot.send_photo(user.user_id, photo=photo, caption=text, parse_mode="Markdown")
                        else:
                            await self.bot.send_message(user.user_id, text, parse_mode="Markdown")
                    except Exception as e:
                        logging.warning(f"Ошибка рассылки юзеру {user.user_id}: {e}")

        # Удаляем временный график после рассылки (опционально)
        # if chart_path and os.path.exists(chart_path):
        #     os.remove(chart_path)