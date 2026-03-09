import logging
from telegram import Update, LabeledPrice, PreCheckoutQuery
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
    ContextTypes
)
import json
import os
from datetime import datetime

# ===== НАСТРОЙКИ =====
ADMIN_ID = 5793502641  # Твой Telegram ID

# Файлы для хранения данных
PROMOCODES_FILE = "promocodes.json"
SETTINGS_FILE = "settings.json"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ===== РАБОТА С ФАЙЛАМИ =====
def load_promocodes():
    """Загружает промокоды из файла"""
    if os.path.exists(PROMOCODES_FILE):
        with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_promocodes(promocodes):
    """Сохраняет промокоды в файл"""
    with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=2)

def load_settings():
    """Загружает настройки"""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "default_price": 100,  # Цена по умолчанию
        "currency": "RUB",  # RUB или XTR (звезды)
        "admin_profit": 0  # Можно добавить позже
    }

def save_settings(settings):
    """Сохраняет настройки"""
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

def get_available_promocode():
    """Получает первый доступный промокод"""
    promocodes = load_promocodes()
    if promocodes:
        return promocodes[0]  # Просто смотрим первый, но не удаляем
    return None

def remove_promocode(promocode_code):
    """Удаляет промокод после покупки"""
    promocodes = load_promocodes()
    promocodes = [p for p in promocodes if p['code'] != promocode_code]
    save_promocodes(promocodes)

# ===== КОМАНДЫ ПОЛЬЗОВАТЕЛЕЙ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    await update.message.reply_text(
        "👋 Привет! Я бот для продажи промокодов.\n"
        "Команды:\n"
        "/buy - купить промокод\n"
        "/check - проверить наличие и цены\n"
        "/help - помощь"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощь"""
    await update.message.reply_text(
        "Как это работает:\n"
        "1. Отправь /check чтобы узнать есть ли промокоды и их цены\n"
        "2. Выбери промокод и отправь /buy для покупки\n"
        "3. После оплаты получишь промокод"
    )

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка наличия промокодов с ценами"""
    promocodes = load_promocodes()
    settings = load_settings()
    
    if not promocodes:
        await update.message.reply_text("😔 К сожалению, сейчас нет доступных промокодов.")
        return
    
    # Показываем все доступные промокоды с ценами
    text = "🎫 Доступные промокоды:\n\n"
    for i, p in enumerate(promocodes, 1):
        price = p.get('price', settings['default_price'])
        currency_symbol = "⭐" if settings['currency'] == "XTR" else "₽"
        text += f"{i}. Промокод #{i} - {price}{currency_symbol}\n"
    
    text += f"\n💰 Для покупки отправь /buy и номер промокода"
    text += f"\nПример: /buy 1"
    
    await update.message.reply_text(text)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Покупка промокода по номеру"""
    promocodes = load_promocodes()
    settings = load_settings()
    
    if not promocodes:
        await update.message.reply_text("😔 Промокодов нет в наличии.")
        return
    
    # Проверяем, указал ли пользователь номер промокода
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи номер промокода:\n"
            "/buy 1 - купить первый промокод\n"
            "/buy 2 - купить второй промокод\n\n"
            "Посмотреть номера: /check"
        )
        return
    
    try:
        # Получаем номер промокода (1, 2, 3...)
        promo_index = int(context.args[0]) - 1
        
        if promo_index < 0 or promo_index >= len(promocodes):
            await update.message.reply_text("❌ Неверный номер промокода")
            return
        
        selected_promo = promocodes[promo_index]
        
        # Получаем цену для этого промокода
        price = selected_promo.get('price', settings['default_price'])
        
        # Сохраняем в контекст, какой промокод покупают
        context.user_data['buying_promocode'] = selected_promo['code']
        
        # Настройка платежа
        chat_id = update.message.chat_id
        title = f"Покупка промокода #{promo_index + 1}"
        description = f"Уникальный промокод"
        payload = f"promo_{selected_promo['code']}"
        currency = settings['currency']
        
        # Для RUB цена в копейках, для XTR (звезды) - как есть
        if currency == "RUB":
            prices = [LabeledPrice(label="Промокод", amount=price * 100)]
        else:
            prices = [LabeledPrice(label="Промокод", amount=price)]
        
        await context.bot.send_invoice(
            chat_id,
            title,
            description,
            payload,
            PAYMENTS_TOKEN,
            currency,
            prices
        )
        
    except ValueError:
        await update.message.reply_text("❌ Используй цифру: /buy 1")

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка перед оплатой"""
    query: PreCheckoutQuery = update.pre_checkout_query
    
    # Проверяем, есть ли еще этот промокод
    promocodes = load_promocodes()
    payload = query.invoice_payload.replace("promo_", "")
    
    # Ищем промокод в списке
    promo_exists = any(p['code'] == payload for p in promocodes)
    
    if not promo_exists:
        await query.answer(ok=False, error_message="Этот промокод уже купили или удалили")
    else:
        await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдача промокода после успешной оплаты"""
    # Получаем промокод, который покупали
    promocode_code = context.user_data.get('buying_promocode')
    
    if not promocode_code:
        await update.message.reply_text("❌ Ошибка: промокод не найден")
        return
    
    # Находим полную информацию о промокоде
    promocodes = load_promocodes()
    promocode_info = next((p for p in promocodes if p['code'] == promocode_code), None)
    
    if promocode_info:
        # Удаляем промокод из списка доступных
        remove_promocode(promocode_code)
        
        # Отправляем пользователю
        await update.message.reply_text(
            f"✅ Оплата прошла успешно!\n"
            f"🎫 Твой промокод: `{promocode_info['code']}`\n\n"
            f"💰 Цена: {promocode_info.get('price', 'стандартная')}\n"
            f"Спасибо за покупку!",
            parse_mode='Markdown'
        )
        
        # Уведомление админу
        await context.bot.send_message(
            ADMIN_ID,
            f"💰 Новая продажа!\n"
            f"👤 Пользователь: @{update.effective_user.username or 'нет юзернейма'} (ID: {update.effective_user.id})\n"
            f"🎫 Промокод: {promocode_info['code']}\n"
            f"💵 Цена: {promocode_info.get('price', 'стандартная')}"
        )
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка: промокод не найден.\n"
            "Свяжись с администратором."
        )
    
    # Очищаем контекст
    context.user_data.clear()

# ===== АДМИН-КОМАНДЫ (ТЫ) =====
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление промокода со своей ценой"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ У тебя нет прав.")
        return
    
    # Формат: /add ПРОМОКОД ЦЕНА
    # или /add ПРОМОКОД (тогда цена по умолчанию)
    try:
        if len(context.args) == 1:
            # Только промокод, цена по умолчанию
            promocode = context.args[0]
            settings = load_settings()
            price = settings['default_price']
        elif len(context.args) >= 2:
            # Промокод и цена
            promocode = context.args[0]
            try:
                price = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Цена должна быть числом")
                return
        else:
            await update.message.reply_text(
                "❌ Использование:\n"
                "/add ПРОМОКОД - добавить с ценой по умолчанию\n"
                "/add ПРОМОКОД ЦЕНА - добавить со своей ценой"
            )
            return
        
        # Добавляем промокод
        promocodes = load_promocodes()
        promocodes.append({
            "code": promocode,
            "price": price,
            "added_date": datetime.now().isoformat()
        })
        save_promocodes(promocodes)
        
        settings = load_settings()
        currency_symbol = "⭐" if settings['currency'] == "XTR" else "₽"
        
        await update.message.reply_text(
            f"✅ Промокод добавлен!\n"
            f"🎫 Код: {promocode}\n"
            f"💰 Цена: {price}{currency_symbol}\n"
            f"📊 Всего промокодов: {len(promocodes)}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def set_default_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить цену по умолчанию"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    try:
        new_price = int(context.args[0])
        settings = load_settings()
        settings['default_price'] = new_price
        save_settings(settings)
        
        currency_symbol = "⭐" if settings['currency'] == "XTR" else "₽"
        await update.message.reply_text(f"✅ Цена по умолчанию установлена: {new_price}{currency_symbol}")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /setprice ЦЕНА")

async def set_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сменить валюту (RUB или XTR)"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    try:
        currency = context.args[0].upper()
        if currency not in ["RUB", "XTR"]:
            await update.message.reply_text("❌ Доступно: RUB или XTR")
            return
        
        settings = load_settings()
        settings['currency'] = currency
        save_settings(settings)
        
        currency_name = "рубли" if currency == "RUB" else "звезды"
        await update.message.reply_text(f"✅ Валюта изменена на {currency_name}")
        
    except IndexError:
        await update.message.reply_text("❌ Использование: /currency RUB или /currency XTR")

async def list_promocodes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все промокоды с ценами"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    promocodes = load_promocodes()
    settings = load_settings()
    
    if not promocodes:
        await update.message.reply_text("📭 Промокодов нет")
        return
    
    currency_symbol = "⭐" if settings['currency'] == "XTR" else "₽"
    
    text = "📋 Доступные промокоды:\n\n"
    total_value = 0
    
    for i, p in enumerate(promocodes, 1):
        price = p.get('price', settings['default_price'])
        total_value += price
        text += f"{i}. `{p['code']}` - {price}{currency_symbol}\n"
        text += f"   📅 {p['added_date'][:10]}\n\n"
    
    text += f"💰 Общая стоимость: {total_value}{currency_symbol}"
    text += f"\n📊 Количество: {len(promocodes)}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def delete_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалить промокод по номеру"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    try:
        index = int(context.args[0]) - 1
        promocodes = load_promocodes()
        
        if 0 <= index < len(promocodes):
            deleted = promocodes.pop(index)
            save_promocodes(promocodes)
            await update.message.reply_text(f"✅ Промокод '{deleted['code']}' удален")
        else:
            await update.message.reply_text("❌ Неверный номер промокода")
            
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /delete НОМЕР")

async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать текущие настройки"""
    user_id = update.effective_user.id
    
    if user_id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    settings = load_settings()
    currency_name = "⭐ Звезды" if settings['currency'] == "XTR" else "₽ Рубли"
    
    text = "⚙️ Текущие настройки:\n\n"
    text += f"💰 Цена по умолчанию: {settings['default_price']} {currency_name}\n"
    text += f"💵 Валюта: {currency_name}\n"
    text += f"👤 Админ ID: {ADMIN_ID}\n"
    
    await update.message.reply_text(text)

# ===== ЗАПУСК БОТА =====
def main():
    """Запуск бота"""
    # Создаем файл настроек, если его нет
    if not os.path.exists(SETTINGS_FILE):
        save_settings(load_settings())
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды для всех пользователей
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("buy", buy))
    
    # Платежные обработчики
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Админ-команды (только для тебя)
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("setprice", set_default_price))
    application.add_handler(CommandHandler("currency", set_currency))
    application.add_handler(CommandHandler("list", list_promocodes))
    application.add_handler(CommandHandler("delete", delete_promocode))
    application.add_handler(CommandHandler("settings", show_settings))
    
    # Запуск
    print("🤖 Бот запущен...")
    print(f"👤 Твой админ ID: {ADMIN_ID}")
    print("💡 Команды админа: /add, /setprice, /currency, /list, /delete, /settings")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()