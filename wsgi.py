import threading
from flask import Flask
from app import on_startup
from aiogram.utils import executor

app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

# Запускаем polling в отдельном потоке
def start_bot():
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
