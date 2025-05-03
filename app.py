import uuid
from flask import Flask, request, jsonify
from yoomoney_api.notification import Notification
from yoomoney_api.quickpay import Quickpay
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import asyncio
from datetime import datetime

# Настройки
YOOMONEY_SECRET = "your_secret_word"  # Секретное слово YooMoney
TELEGRAM_TOKEN = "your_bot_token"  # Токен Telegram-бота
WALLET_NUMBER = "your_wallet_number"  # Номер кошелька YooMoney
GROUP_ID = "your_group_id"  # ID закрытой группы (например, -100123456789)
SUBSCRIPTION_AMOUNT = 100  # Стоимость подписки в рублях

# Инициализация
app = Flanagan(__name__)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

# Инициализация SQLite
def init_db():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS payments
                 (user_id TEXT, amount REAL, label TEXT, datetime TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

# API для генерации ссылки на оплату
@app.route('/generate_payment', methods=['GET'])
def generate_payment():
    user_id = request.args.get('user_id')
    label = str(uuid.uuid4())  # Уникальный идентификатор платежа
    quickpay = Quickpay(
        receiver=WALLET_NUMBER,
        quickpay_form="shop",
        sum=SUBSCRIPTION_AMOUNT,
        label=label,
        payment_type="AC"
    )
    # Сохраняем временную запись о платеже
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, amount, label, status) VALUES (?, ?, ?, ?)",
              (user_id, SUBSCRIPTION_AMOUNT, label, "pending"))
    conn.commit()
    conn.close()
    return jsonify({"payment_url": quickpay.redirected_url, "label": label})

# Webhook для YooMoney
@app.route('/yoomoney-webhook', methods=['POST'])
async def webhook():
    data = request.form.to_dict()
    notification = Notification(data, YOOMONEY_SECRET)
    if not notification.is_valid():
        return "Invalid notification", 400

    if data.get('notification_type') == 'p2p-incoming':
        label = data.get('label')
        amount = float(data.get('amount'))
        # Обновляем статус платежа
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("UPDATE payments SET status = ?, datetime = ? WHERE label = ?",
                  ("completed", datetime.now().isoformat(), label))
        c.execute("SELECT user_id FROM payments WHERE label = ?", (label,))
        user_id = c.fetchone()[0]
        conn.commit()
        conn.close()
        # Генерируем инвайт-ссылку
        invite_link = await bot.create_chat_invite_link(chat_id=GROUP_ID, member_limit=1)
        # Отправляем уведомление и ссылку
        await bot.send_message(user_id, f"Оплата успешна! Сумма: {amount} RUB\nВаша подписка активирована.\nПрисоединяйтесь: {invite_link.invite_link}")
    return "OK", 200

# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Оплатить подписку", callback_data="pay_subscription"))
    await message.reply("Нажмите, чтобы оформить подписку:", reply_markup=keyboard)

# Обработка кнопки оплаты
@dp.callback_query_handler(text="pay_subscription")
async def process_payment(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    # Запрашиваем ссылку на оплату через API
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://your-app.onrender.com/generate_payment?user_id={user_id}") as resp:
            data = await resp.json()
            payment_url = data["payment_url"]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Оплатить", url=payment_url))
    await callback.message.edit_text("Перейдите по ссылке для оплаты:", reply_markup=keyboard)

# Запуск бота
async def on_startup(_):
    print("Бот запущен")

if __name__ == "__main__":
    # Запускаем Flask и aiogram
    from threading import Thread
    flask_thread = Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    flask_thread.start()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
