import logging
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import json
from datetime import datetime
import asyncio

# ===== ТВОИ ДАННЫЕ =====
BOT_TOKEN = "8797991386:AAEo-fimvtVUV7x8uP-UcJFaydtCE35xFos"
YOUR_TON_WALLET = "UQAd58qFkfxh_mQCTsvzK7Sr9QIllgeaCOHxHUcsCW8_pBsU"  # Твой TON кошелек
ADMIN_ID = 5793502641

# Курс TON к рублю (примерный, можешь менять)
TON_PRICE_IN_RUB = 150  # 1 TON = 150 рублей

# Файлы для хранения данных
PROMOCODES_FILE = "promocodes.json"
SETTINGS_FILE = "settings.json"
TRANSACTIONS_FILE = "transactions.json"

# Настройка логирования
logging.basicConfig(
    format='%(asname)time)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

print("="*50)
print("🚀 ЗАПУСК БОТА С ОПЛАТОЙ В TON")
print("="*50)
print(f"🤖 Токен бота: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:]}")
print(f"💎 TON кошелек: {YOUR_TON_WALLET[:10]}...{YOUR_TON_WALLET[-5:]}")
print(f"👤 ID админа: {ADMIN_ID}")
print(f"💰 Курс: 1 TON = {TON_PRICE_IN_RUB} RUB")
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
        "default_price_rub": 100,  # Цена в рублях
        "ton_price_rub": TON_PRICE_IN_RUB
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

def load_transactions():
    """Загружает историю транзакций"""
    if os.path.exists(TRANSACTIONS_FILE):
        try:
            with open(TRANSACTIONS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_transaction(user_id, username, promocode, price_rub, price_ton, tx_hash=None):
    """Сохраняет информацию о транзакции"""
    transactions = load_transactions()
    transactions.append({
        "user_id": user_id,
        "username": username,
        "promocode": promocode,
        "price_rub": price_rub,
        "price_ton": price_ton,
        "tx_hash": tx_hash,
        "status": "pending",
        "date": datetime.now().isoformat()
    })
    with open(TRANSACTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, ensure_ascii=False, indent=2)

def update_transaction_status(tx_hash, status):
    """Обновляет статус транзакции"""
    transactions = load_transactions()
    for tx in transactions:
        if tx.get("tx_hash") == tx_hash:
            tx["status"] = status
            break
    with open(TRANSACTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(transactions, f, ensure_ascii=False, indent=2)

# ===== ФУНКЦИИ БОТА =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветственное сообщение"""
    keyboard = [
        [InlineKeyboardButton("🛒 Купить промокод", callback_data="buy_menu")],
        [InlineKeyboardButton("🔍 Проверить наличие", callback_data="check")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Привет! Я бот для продажи промокодов CipherChats\n\n"
        "💎 Оплата через Telegram Wallet\n"
        "💰 Цены в TON (1 TON ≈ 150 RUB)\n\n"
        "Выбери действие:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy_menu":
        await show_buy_menu(query, context)
    elif query.data == "check":
        await check_promocodes(query, context)
    elif query.data == "help":
        await show_help(query, context)
    elif query.data.startswith("buy_"):
        # Формат: buy_ИНДЕКС
        index = int(query.data.split("_")[1])
        await process_buy(query, context, index)

async def show_buy_menu(query, context):
    """Показывает меню покупки"""
    promocodes = load_promocodes()
    settings = load_settings()
    
    if not promocodes:
        await query.edit_message_text(
            "😔 К сожалению, сейчас нет доступных промокодов.\n"
            "Загляни позже!"
        )
        return
    
    text = "🎫 Доступные промокоды:\n\n"
    keyboard = []
    
    for i, p in enumerate(promocodes, 1):
        price_rub = p.get('price_rub', settings['default_price_rub'])
        price_ton = round(price_rub / settings['ton_price_rub'], 2)
        text += f"{i}. Промокод #{i}\n"
        text += f"   💰 {price_rub} RUB | {price_ton} TON\n"
        text += f"   📅 Добавлен: {p['added_date'][:10]}\n\n"
        
        # Кнопка для покупки
        keyboard.append([InlineKeyboardButton(
            f"✅ Купить #{i} за {price_ton} TON", 
            callback_data=f"buy_{i-1}"
        )])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def check_promocodes(query, context):
    """Проверка наличия промокодов"""
    promocodes = load_promocodes()
    settings = load_settings()
    
    if not promocodes:
        text = "😔 Промокодов нет в наличии."
    else:
        text = f"✅ Доступно промокодов: {len(promocodes)}\n\n"
        for i, p in enumerate(promocodes, 1):
            price_rub = p.get('price_rub', settings['default_price_rub'])
            price_ton = round(price_rub / settings['ton_price_rub'], 2)
            text += f"{i}. {price_ton} TON ({price_rub} RUB)\n"
    
    keyboard = [[InlineKeyboardButton("🛒 Купить", callback_data="buy_menu")],
                [InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup)

async def show_help(query, context):
    """Показывает помощь"""
    text = (
        "❓ Как купить промокод:\n\n"
        "1. Нажми 'Купить промокод'\n"
        "2. Выбери нужный промокод\n"
        "3. Отправь TON на указанный кошелек\n"
        "4. После оплаты пришли скриншот или хеш транзакции\n"
        "5. Получи промокод!\n\n"
        "💎 Кошелек для оплаты:\n"
        f"`{YOUR_TON_WALLET}`\n\n"
        "⚠️ Внимание: перевод только в сети TON"
    )
    
    keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def process_buy(query, context, index):
    """Обработка покупки"""
    promocodes = load_promocodes()
    settings = load_settings()
    
    if index < 0 or index >= len(promocodes):
        await query.edit_message_text("❌ Ошибка: промокод не найден")
        return
    
    selected = promocodes[index]
    price_rub = selected.get('price_rub', settings['default_price_rub'])
    price_ton = round(price_rub / settings['ton_price_rub'], 2)
    
    # Сохраняем в контекст
    context.user_data['buying_index'] = index
    context.user_data['buying_code'] = selected['code']
    context.user_data['buying_price_ton'] = price_ton
    context.user_data['buying_price_rub'] = price_rub
    
    text = (
        f"🎫 Промокод: #{index + 1}\n"
        f"💰 Цена: {price_ton} TON ({price_rub} RUB)\n\n"
        f"💎 Отправь точно {price_ton} TON на кошелек:\n"
        f"`{YOUR_TON_WALLET}`\n\n"
        f"📤 После отправки нажми 'Я оплатил' и пришли хеш транзакции"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{index}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="buy_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def paid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия 'Я оплатил'"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📤 Отправь хеш транзакции (tx hash) или скриншот оплаты.\n\n"
        "Хеш можно найти в истории транзакций Telegram Wallet\n\n"
        "Пример: 0x1a2b3c... или просто отправь фото"
    )
    context.user_data['waiting_for_payment'] = True

async def handle_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка подтверждения оплаты"""
    if not context.user_data.get('waiting_for_payment'):
        return
    
    user = update.effective_user
    message = update.message
    
    # Получаем данные о покупке
    index = context.user_data.get('buying_index')
    promocode = context.user_data.get('buying_code')
    price_ton = context.user_data.get('buying_price_ton')
    price_rub = context.user_data.get('buying_price_rub')
    
    if not all([index is not None, promocode, price_ton]):
        await message.reply_text("❌ Ошибка: начни покупку заново /start")
        return
    
    # Сохраняем транзакцию
    tx_hash = message.text if message.text else "скриншот"
    save_transaction(
        user.id, 
        user.username, 
        promocode, 
        price_rub, 
        price_ton, 
        tx_hash
    )
    
    # Уведомление админу
    admin_text = (
        f"💰 Новая оплата!\n\n"
        f"👤 Пользователь: @{user.username or 'нет'} (ID: {user.id})\n"
        f"🎫 Промокод: {promocode}\n"
        f"💵 Сумма: {price_ton} TON ({price_rub} RUB)\n"
        f"📤 Хеш/скрин: {tx_hash}\n\n"
        f"Проверь оплату и выдай промокод командой:\n"
        f"/confirm_{user.id}_{promocode}"
    )
    
    await context.bot.send_message(ADMIN_ID, admin_text)
    
    await message.reply_text(
        "✅ Запрос отправлен админу!\n"
        "Как только оплата подтвердится, ты получишь промокод."
    )
    
    context.user_data['waiting_for_payment'] = False

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-команда для подтверждения оплаты"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа")
        return
    
    try:
        # Формат: /confirm_USERID_PROMOCODE
        parts = update.message.text.split('_')
        user_id = int(parts[1])
        promocode = parts[2]
        
        # Удаляем промокод из списка
        promocodes = load_promocodes()
        promocodes = [p for p in promocodes if p['code'] != promocode]
        save_promocodes(promocodes)
        
        # Отправляем промокод пользователю
        await context.bot.send_message(
            user_id,
            f"✅ Оплата подтверждена!\n"
            f"🎫 Твой промокод: `{promocode}`\n"
            f"Спасибо за покупку!",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(f"✅ Промокод {promocode} выдан пользователю {user_id}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# ===== АДМИН-КОМАНДЫ =====
async def add_promocode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление промокода"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    try:
        if len(context.args) == 1:
            promocode = context.args[0]
            settings = load_settings()
            price_rub = settings['default_price_rub']
        elif len(context.args) >= 2:
            promocode = context.args[0]
            try:
                price_rub = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Цена должна быть числом (в рублях)")
                return
        else:
            await update.message.reply_text(
                "❌ Использование:\n"
                "/add ПРОМОКОД - добавить с ценой по умолчанию\n"
                "/add ПРОМОКОД ЦЕНА_В_РУБЛЯХ - добавить со своей ценой"
            )
            return
        
        promocodes = load_promocodes()
        promocodes.append({
            "code": promocode,
            "price_rub": price_rub,
            "added_date": datetime.now().isoformat()
        })
        save_promocodes(promocodes)
        
        settings = load_settings()
        price_ton = round(price_rub / settings['ton_price_rub'], 2)
        
        await update.message.reply_text(
            f"✅ Промокод добавлен!\n"
            f"🎫 Код: {promocode}\n"
            f"💰 Цена: {price_rub} RUB | {price_ton} TON\n"
            f"📊 Всего промокодов: {len(promocodes)}"
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def set_ton_rate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Установить курс TON к рублю"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    try:
        new_rate = int(context.args[0])
        settings = load_settings()
        settings['ton_price_rub'] = new_rate
        save_settings(settings)
        
        await update.message.reply_text(f"✅ Курс TON установлен: 1 TON = {new_rate} RUB")
        
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Использование: /setrate ЦЕНА_В_РУБЛЯХ")

async def list_promocodes_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать все промокоды (для админа)"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    promocodes = load_promocodes()
    settings = load_settings()
    
    if not promocodes:
        await update.message.reply_text("📭 Промокодов нет")
        return
    
    text = "📋 Доступные промокоды:\n\n"
    total_rub = 0
    
    for i, p in enumerate(promocodes, 1):
        price_rub = p.get('price_rub', settings['default_price_rub'])
        price_ton = round(price_rub / settings['ton_price_rub'], 2)
        total_rub += price_rub
        text += f"{i}. `{p['code']}`\n"
        text += f"   💰 {price_rub} RUB | {price_ton} TON\n"
        text += f"   📅 {p['added_date'][:10]}\n\n"
    
    total_ton = round(total_rub / settings['ton_price_rub'], 2)
    text += f"💰 Общая стоимость: {total_rub} RUB | {total_ton} TON"
    text += f"\n📊 Количество: {len(promocodes)}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def delete_promocode_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def show_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать историю транзакций"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет доступа.")
        return
    
    transactions = load_transactions()
    if not transactions:
        await update.message.reply_text("📭 Транзакций нет")
        return
    
    text = "📊 История продаж:\n\n"
    for tx in transactions[-10:]:  # последние 10
        text += f"👤 {tx['username'] or tx['user_id']}\n"
        text += f"🎫 {tx['promocode']}\n"
        text += f"💰 {tx['price_ton']} TON ({tx['price_rub']} RUB)\n"
        text += f"📅 {tx['date'][:19]}\n"
        text += f"📤 {tx.get('tx_hash', 'скрин')[:20]}...\n"
        text += f"📊 Статус: {tx['status']}\n\n"
    
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
    
    if not os.path.exists(TRANSACTIONS_FILE):
        save_transaction("init", "init", "init", 0, 0, "init")
        print("✅ Создан файл транзакций")
    
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Команды для всех
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback, pattern="^(?!paid_).*$"))
    application.add_handler(CallbackQueryHandler(paid_callback, pattern="^paid_"))
    
    # Обработка сообщений (подтверждение оплаты)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_payment_proof))
    application.add_handler(MessageHandler(filters.PHOTO, handle_payment_proof))
    
    # Админ-команды
    application.add_handler(CommandHandler("add", add_promocode))
    application.add_handler(CommandHandler("setrate", set_ton_rate))
    application.add_handler(CommandHandler("list", list_promocodes_admin))
    application.add_handler(CommandHandler("delete", delete_promocode_admin))
    application.add_handler(CommandHandler("transactions", show_transactions))
    application.add_handler(CommandHandler("confirm", confirm_payment))
    
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