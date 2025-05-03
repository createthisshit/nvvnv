from app import bot, dp, on_startup
from aiogram.utils import executor
import asyncio

# Запускаем polling в асинхронном режиме
def run_bot():
    loop = asyncio.get_event_loop()
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup, loop=loop)

# Минимальное WSGI-приложение для Render
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

if __name__ == "__main__":
    run_bot()
