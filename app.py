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

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Настройки
TOKEN = "7629991596:AAHkBKWyvz7T2MdaItlQcL90YnOi0Zh11tY"  # Токен Telegram-бота
YOOMONEY_WALLET = "4100118178122985"  # Номер кошелька YooMoney
YOOMONEY_SECRET = "CoqQlgE3E5cTzyAKY1LSiLU1"  # Секретное слово YooMoney
YOOMONEY_AMOUNT = 1  # Сумма подписки в рублях
GROUP_ID = -1002291268265  # ID закрытой группы
BASE_URL = "https://nvvnv.onrender.com"  # Адрес сервера

# Инициализация Flask
app = Flask(__name__)

# Инициализация бота
try:
    bot = Bot(token=TOKEN)
    logger.info("Бот инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации бота: {e}")
    sys.exit(1)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Инициализация SQLite
def init_db():
    try:
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS payments
                     (user_id TEXT, amount REAL, label TEXT, datetime TEXT, status TEXT)''')
        conn.commit()
        conn.close()
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        sys.exit(1)

init_db()

# API для генерации ссылки на оплату
@app.route('/generate_payment', methods=['GET'])
def generate_payment():
    try:
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
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute("INSERT INTO payments (user_id, amount, label, status) VALUES (?, ?, ?, ?)",
                  (user_id, YOOMONEY_AMOUNT, label, "pending"))
        conn.commit()
        conn.close()
        logger.info(f"Сгенерирована ссылка для user_id={user_id}, label={label}")
        return jsonify({"payment_url": payment_url, "label": label})
    except Exception as e:
        logger.error(f"Ошибка в /generate_payment: {e}")
        return jsonify({"error": str(e)}), 500

# Webhook для YooMoney
@app.route('/yoomoney-webhook', methods=['POST'])
async def webhook():
    try:
        data = request.form.to_dict()
        logger.info(f"Получено уведомление YooMoney: {data}")
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
            logger.error("Неверный SHA1-хэш")
            return "Invalid notification", 400

        if data.get('notification_type') == 'p2p-incoming':
            label = data.get('label')
            amount = float(data.get('amount'))
            conn = sqlite3.connect('data.db')
            c = conn.cursor()
            c.execute("UPDATE payments SET status = ?, datetime = ? WHERE label = ?",
                      ("completed", datetime.now().isoformat(), label))
            c.execute("SELECT user_id FROM payments WHERE label = ?", (label,))
            user_id = c.fetchone()[0]
            conn.commit()
            conn.close()
            logger.info(f"Оплата успешна для user_id={user_id}, label={label}")
            await bot.send_message(user_id, "Успешно")
            invite_link = await bot.create_chat_invite_link(chat_id=GROUP_ID, member_limit=1)
            await bot.send_message(user_id, f"Присоединяйтесь: {invite_link.invite_link}")
        return "OK", 200
    except Exception as e:
        logger.error(f"Ошибка в /yoomoney-webhook: {e}")
        return jsonify({"error": str(e)}), 500

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    try:
        user_id = str(message.from_user.id)
        logger.info(f"Получена команда /start от user_id={user_id}")
        response = requests.get(f"{BASE_URL}/generate_payment?user_id={user_id}")
        response.raise_for_status()
        data = response.json()
        payment_url = data["payment_url"]

        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Пополнить", url=payment_url))
        welcome_text = (
            "Тариф: фулл\n"
            "Стоимость: 500.00 🇷🇺RUB\n"
            "Срок действия: 1 месяц\n\n"
            "Вы получите доступ к следующим ресурсам:\n"
            "• Мой кайф (канал)"
        )
        await message.answer(welcome_text, reply_markup=keyboard)
        logger.info(f"Отправлен ответ на /start для user_id={user_id}")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /start: {e}")
        await message.answer("Произошла ошибка, попробуйте позже.")

# Запуск бота
def on_startup(_):
    logger.info("Бот запущен")

def run_flask():
    try:
        logger.info("Запуск Flask-сервера")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Ошибка запуска Flask: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        logger.info("Запуск приложения")
        from threading import Thread
        flask_thread = Thread(target=run_flask)
        flask_thread.start()
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        sys.exit(1)
