import threading
from flask import Flask
from app import start_bot

# Минимальное Flask-приложение для Gunicorn
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

# Запускаем бот в отдельном потоке
threading.Thread(target=start_bot, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
