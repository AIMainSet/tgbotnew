"""
Улучшенное форматирование сигналов с рейтингом
"""
from typing import Dict
import numpy as np


class EnhancedSignalFormatter:
    @staticmethod
    def format_signal_with_rating(signal: Dict, rating: Dict = None) -> str:
        """Форматирование сигнала с рейтингом"""

        if signal['direction'] == 'LONG':
            direction_emoji = "🟢"
            arrow = "📈"
            direction_text = "ПОКУПКА (LONG)"
            action_verb = "Покупайте"
            trend = "роста"
        else:
            direction_emoji = "🔴"
            arrow = "📉"
            direction_text = "ПРОДАЖА (SHORT)"
            action_verb = "Продавайте"
            trend = "падения"

        # Определяем рейтинг
        if rating:
            rating_emoji = rating.get('emoji', '⭐')
            rating_text = rating.get('status', 'STANDARD')
            confidence = rating.get('confidence', 0.5) * 100
        else:
            rating_emoji = "⭐"
            rating_text = "STANDARD"
            confidence = 50

        # Рассчитываем проценты
        tp1_percent = EnhancedSignalFormatter.calculate_percentage(signal['entry'], signal['tp1'])
        tp2_percent = EnhancedSignalFormatter.calculate_percentage(signal['entry'], signal.get('tp2', 0))
        tp3_percent = EnhancedSignalFormatter.calculate_percentage(signal['entry'], signal.get('tp3', 0))
        sl_percent = EnhancedSignalFormatter.calculate_percentage(signal['entry'], signal.get('sl', 0))

        # Форматируем сообщение
        message = f"""
{direction_emoji} <b>{rating_emoji} КРИПТО-СИГНАЛ {rating_text}</b> {arrow}

💰 <b>Торговая пара:</b> <code>{signal['symbol']}</code>
🎯 <b>Тип сделки:</b> {direction_text}
💵 <b>Цена входа:</b> ${signal['entry']:.2f}
📊 <b>Уверенность:</b> {confidence:.1f}%

<b>🎯 УРОВНИ ТЕЙК-ПРОФИТА:</b>
✅ <b>TP1:</b> ${signal['tp1']:.2f} (<code>+{tp1_percent:.2f}%</code>)
✅ <b>TP2:</b> ${signal.get('tp2', 0):.2f} (<code>+{tp2_percent:.2f}%</code>)
✅ <b>TP3:</b> ${signal.get('tp3', 0):.2f} (<code>+{tp3_percent:.2f}%</code>)

<b>⛔ УРОВЕНЬ СТОП-ЛОСС:</b>
🔻 <b>SL:</b> ${signal.get('sl', 0):.2f} (<code>{sl_percent:+.2f}%</code>)

<b>⚖️ РИСК-МЕНЕДЖМЕНТ:</b>
• <b>Риск:</b> {signal.get('risk', 'Medium')}
• <b>Соотношение риск/прибыль:</b> 1:{signal.get('risk_reward', 2):.1f}
• <b>Рек. размер позиции:</b> 2-5% от депозита

<b>📈 ОБОСНОВАНИЕ СИГНАЛА:</b>
{signal.get('reason', 'Анализ технических индикаторов')}

<b>💡 РЕКОМЕНДАЦИИ:</b>
• {action_verb} {signal['symbol']} по цене ${signal['entry']:.2f}
• Разместите стоп-лосс на ${signal.get('sl', 0):.2f}
• Частично фиксируйте прибыль на уровнях TP1-3
• Ожидайте движения цены в сторону {trend}

<b>⚠️ ВНИМАНИЕ:</b>
Криптовалюты — высокорисковые активы.
Торгуйте только на деньги, которые можете позволить себе потерять.

🕒 <i>Сигнал сгенерирован: {signal.get('created_at', 'N/A')}</i>
"""

        return message

    @staticmethod
    def format_signal_result(result: Dict) -> str:
        """Форматирование результата сигнала"""

        if result['status'].startswith('SUCCESS'):
            emoji = "✅"
            title = "СДЕЛКА ЗАКРЫТА С ПРИБЫЛЬЮ"
            color = "🟢"
        elif result['status'] == 'STOP_LOSS':
            emoji = "⛔"
            title = "СДЕЛКА ЗАКРЫТА ПО СТОП-ЛОССУ"
            color = "🔴"
        elif 'IN_PROGRESS' in result['status']:
            emoji = "⏳"
            title = "СДЕЛКА В ПРОЦЕССЕ"
            color = "🟡"
        else:
            emoji = "❓"
            title = "СТАТУС НЕИЗВЕСТЕН"
            color = "⚪"

        pnl_emoji = "📈" if result.get('pnl_percent', 0) >= 0 else "📉"

        message = f"""
{color} <b>{emoji} {title}</b> {emoji}

💰 <b>Пара:</b> {result['symbol']}
🎯 <b>Направление:</b> {result['direction']}
💵 <b>Цена входа:</b> ${result.get('entry_price', 0):.2f}
📊 <b>Текущая цена:</b> ${result.get('current_price', 0):.2f}

{bpnl_emoji} <b>ПРИБЫЛЬ/УБЫТОК:</b>
• <b>Абсолютный:</b> ${abs(result.get('pnl_absolute', 0)):.2f}
• <b>Процентный:</b> {result.get('pnl_percent', 0):+.2f}%

📋 <b>ДЕТАЛИ:</b>
• <b>Статус:</b> {result['status']}
• <b>Сработавший уровень:</b> {result.get('hit_level', 'N/A')}
• <b>Время в сделке:</b> {result.get('time_elapsed', 'N/A')}

{'🎉 Отличная работа!' if result['status'].startswith('SUCCESS') else '🔄 Учимся на каждой сделке!' if result['status'] == 'STOP_LOSS' else '⏳ Ожидаем результата...'}
"""

        return message

    @staticmethod
    def format_statistics(stats: Dict) -> str:
        """Форматирование статистики"""

        if not stats:
            return "📊 Статистика пока недоступна"

        message = f"""
📊 <b>СТАТИСТИКА ТОЧНОСТИ СИГНАЛОВ</b>

📈 <b>ОБЩАЯ СТАТИСТИКА:</b>
• Всего сигналов: {stats.get('total_signals', 0)}
• Успешных сделок: {stats.get('successful', 0)}
• Стоп-лоссов: {stats.get('stop_loss', 0)}
• В процессе: {stats.get('in_progress', 0)}

🎯 <b>ТОЧНОСТЬ:</b>
• Успешность: {stats.get('success_rate', 0):.1f}%
• Процент стоп-лоссов: {stats.get('stop_loss_rate', 0):.1f}%

💰 <b>ПРИБЫЛЬНОСТЬ:</b>
• Средняя прибыль: {stats.get('avg_profit', 0):.2f}%
• Средний убыток: {stats.get('avg_loss', 0):.2f}%
• Фактор прибыли: {stats.get('profit_factor', 0):.2f}
• Ожидаемая доходность: {stats.get('expected_value', 0):.3f}

📅 <i>Обновлено: {stats.get('last_update', 'N/A')}</i>
"""

        return message

    @staticmethod
    def calculate_percentage(entry: float, target: float) -> float:
        """Расчет процентного изменения"""
        return ((target - entry) / entry) * 100