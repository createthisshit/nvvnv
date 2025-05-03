import uuid
import requests
import asyncio
import logging
import sys
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from glQiwiApi import YooMoneyAPI
from glQiwiApi.utils import YooMoneyNotification

# Настройки
TOKEN = "7629991596:AAHkBKWyvz7T2MdaItlQcL90YnOi0Zh11tY"  # Токен Telegram-бота
YOOMONEY_WALLET = "4100118178122985"  # Номер кошелька YooMoney
YOOMONEY_SECRET = "CoqQlgE3E5cTzyAKY1LSiLU1"  # Секретное слово YooMoney
YOOMONEY_AMOUNT = 1  # Сумма подписки в рублях
GROUP_ID = -1002291268265  # ID закрытой группы
BASE_URL = "https://nvvnv.onrender.com"  # Замени на URL после деплоя

import uuid
import requests
import asyncio
import logging
import sys
import sqlite3
import hashlib
from datetime import datetime
from flask import Flask, request, jsonify
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

# Настройки
TOKEN = "7629991596:AAHkBKWyvz7T2MdaItlQcL90YnOi0Zh11tY"  # Токен Telegram-бота
YOOMONEY_WALLET = "4100118178122985"  # Номер кошелька YooMoney
YOOMONEY_SECRET = "CoqQlgE3E5cTzyAKY1LSiLU1"  # Секретное слово YooMoney
YOOMONEY_AMOUNT = 1  # Сумма подписки в рублях
GROUP_ID = -1002291268265  # ID закрытой группы
BASE_URL = "https://nvvnv.onrender.com"  # Указан твой URL

# Инициализация Flask
app = Flask(__name__)

# Инициализация бота
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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
    label = str(uuid.uuid4())
    payment_url = (
        f"https://yoomoney.ru/quickpay/confirm.xml?"
        f"receiver={YOOMONEY_WALLET}&"
        f"quickpay-form=shop&"
        f"targets=Subscription&"
        f"paymentType=AC&"
        f"sum={YOOMONEY_AMOUNT}&"
        f"label={label}"
    )
    # Сохраняем временную запись о платеже
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute("INSERT INTO payments (user_id, amount, label, status) VALUES (?, ?, ?, ?)",
              (user_id, YOOMONEY_AMOUNT, label, "pending"))
    conn.commit()
    conn.close()
    return jsonify({"payment_url": payment_url, "label": label})

# Webhook для YooMoney
@app.route('/yoomoney-webhook', methods=['POST'])
async def webhook():
    data = request.form.to_dict()
    # Проверка подлинности уведомления
    params = [
        data.get('notification_type', ''),
        data.get('operation_id', ''),
        data.get('amount', ''),
        data.get('currency', ''),
        data.get('datetime', ''),
        data.get('sender', ''),
        data.get('codepro', ''),
        YOOMONEY_SECRET,
        data.get('label', '')
    ]
    check_string = '&'.join(params)
    sha1_hash = hashlib.sha1(check_string.encode()).hexdigest()
    if sha1_hash != data.get('sha1_hash'):
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

# Обработчик сообщений
@dp.message_handler(content_types=types.ContentType.ANY)
async def command_start_handler(message: types.Message):
    user_id = str(message.from_user.id)
    # Запрашиваем ссылку на оплату через API
    response = requests.get(f"{BASE_URL}/generate_payment?user_id={user_id}")
    data = response.json()
    payment_url = data["payment_url"]

    # Создаем кнопки
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton(text="Оплатить", url=payment_url))
    welcome_text = (
        "Тариф: фулл\n"
        "Стоимость: 500.00 🇷🇺RUB\n"
        "Срок действия: 1 месяц\n\n"
        "Вы получите доступ к следующим ресурсам:\n"
        "• Мой кайф (канал)"
    )
    await message.answer(welcome_text, reply_markup=keyboard)

# Запуск бота
def on_startup(_):
    print("Бот запущен")

def run_flask():
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    # Запускаем Flask в отдельном потоке
    from threading import Thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    # Запускаем бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
