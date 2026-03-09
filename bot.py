import logging
import os
import sys
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
from datetime import datetime

# ===== ТВОИ ДАННЫЕ (УЖЕ ВСТАВЛЕНЫ) =====
BOT_TOKEN = "8797991386:AAEo-fimvtVUV7x8uP-UcJFaydtCE35xFos"
PAYMENTS_TOKEN = "5775769170:LIVE:TG_HPikr11oRkQvZ0l9peLHbg4A"
ADMIN_ID = 5793502641

# Файлы для хранения данных
PROMOCODES_FILE = "promocodes.json"
SETTINGS_FILE = "settings.json"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("="*50)
print("🚀 ЗАПУСК БОТА НА RAILWAY")
print("="*50)
print(f"🤖 Токен бота: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
print(f"💳 Токен платежей: {PAYMENTS_TOKEN[:10]}...{PAYMENTS_TOKEN[-5:]}")
print(f"👤 ID админа: {ADMIN_ID}")
print("="*50)

# ===== РАБОТА С ФАЙЛАМИ =====
def load_promocodes():
    """Загружает промокоды из файла"""
    if os.path.exists(PROMOCODES_FILE):
        try:
            with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки промокодов: {e}")
            return []
    return []

def save_promocodes(promocodes):
    """Сохраняет промокоды в файл"""
    try:
        with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(promocodes, f, ensure_ascii=False, indent=2)
        print(f"✅ Промокоды сохранены: {len(promocodes)} шт.")
    except Exception as e:
        print(f"❌ Ошибка сохранения промокодов: {e}")

def load_settings():
    """Загружает настройки"""
    default_settings = {
        "default_price": 100,
        "currency": "RUB"
    }
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки настроек: {e}")
            return default_settings
    return default_settings

def save_settings(settings):
    """Сохраняет настройки"""
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения настроек: {e}")

# ===== ФУНКЦИИ БОТА =====
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
    
    if not context.args:
        await update.message.reply_text(
            "❌ Укажи номер промокода:\n"
            "/buy 1 - купить первый промокод\n"
            "/buy 2 - купить второй промокод\n\n"
            "Посмотреть номера: /check"
        )
        return
    
    try:
        promo_index = int(context.args[0]) - 1
        
        if promo_index < 0 or promo_index >= len(promocodes):
            await update.message.reply_text("❌ Неверный номер промокода")
            return
        
        selected_promo = promocodes[promo_index]
        price = selected_promo.get('price', settings['default_price'])
        
        context.user_data['buying_promocode'] = selected_promo['code']
        context.user_data['buying_price'] = price
        
        chat_id = update.message.chat_id
        title = f"Покупка промокода #{promo_index + 1}"
        description = f"Уникальный промокод"
        payload = f"promo_{selected_promo['code']}"
        currency = settings['currency']
        
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
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка перед оплатой"""
    query: PreCheckoutQuery = update.pre_checkout_query
    
    promocodes = load_promocodes()
    payload = query.invoice_payload.replace("promo_", "")
    
    promo_exists = any(p['code'] == payload for p in promocodes)
    
    if not promo_exists:
        await query.answer(ok=False, error_message="Этот промокод уже купили или удалили")
    else:
        await query.answer(ok=True)

async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выдача промокода после успешной оплаты"""
    promocode_code = context.user_data.get('buying_promocode')
    
    if not promocode_code:
        await update.message.reply_text("❌ Ошибка: промокод не найден")
        return
    
    promocodes = load_promocodes()
    promocode_info = next((p for p in promocodes if p['code'] == promocode_code), None)
    
    if promocode_info:
        # Удаляем промокод
        promocodes = [p for p in promocodes if p['code'] != promocode_code]
        save_promocodes(promocodes)
        
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
        await update.message.reply_text("❌ Ошибка: промокод не найден")
    
    context.user_data.clear()

# ===== АДМИН-КОМАНДЫ =====
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление промокода"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    try:
        if len(context.args) == 1:
            promocode = context.args[0]
            settings = load_settings()
            price = settings['default_price']
        elif len(context.args) >= 2:
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
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    try:
        new_price = int(context.args[0])
        settings = load_settings()
        settings['default_price'] = new_price
        save_settings(settings)
        
        currency_symbol = "⭐" if settings['currency'] == "XTR" else "₽"
        await update.message.reply_text(f"✅ Цена по умолчанию: {new_price}{currency_symbol}")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /setprice ЦЕНА")

async def set_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сменить валюту"""
    if update.effective_user.id != ADMIN_ID:
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
    """Показать все промокоды"""
    if update.effective_user.id != ADMIN_ID:
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
    """Удалить промокод"""
    if update.effective_user.id != ADMIN_ID:
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
    """Показать настройки"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    settings = load_settings()
    currency_name = "⭐ Звезды" if settings['currency'] == "XTR" else "₽ Рубли"
    
    text = "⚙️ Текущие настройки:\n\n"
    text += f"💰 Цена по умолчанию: {settings['default_price']} {currency_name}\n"
    text += f"💵 Валюта: {currency_name}\n"
    text += f"👤 Твой ID: {ADMIN_ID}\n"
    text += f"📁 Промокодов в базе: {len(load_promocodes())}"
    
    await update.message.reply_text(text)

# ===== ЗАПУСК БОТА =====
def main():
    """Запуск бота"""
    # Создаем файлы, если их нет
    if not os.path.exists(SETTINGS_FILE):
        save_settings(load_settings())
        print("✅ Создан файл настроек")
    
    if not os.path.exists(PROMOCODES_FILE):
        save_promocodes([])
        print("✅ Создан файл промокодов")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды для всех
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check))
    application.add_handler(CommandHandler("buy", buy))
    
    # Платежные обработчики
    application.add_handler(PreCheckoutQueryHandler(pre_checkout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    
    # Админ-команды
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("setprice", set_default_price))
    application.add_handler(CommandHandler("currency", set_currency))
    application.add_handler(CommandHandler("list", list_promocodes))
    application.add_handler(CommandHandler("delete", delete_promocode))
    application.add_handler(CommandHandler("settings", show_settings))
    
    # Запуск
    print("✅ Бот готов к работе! Запускаем polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()