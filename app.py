import logging
import sys
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
TOKEN = "7241683107:AAEG6RCRM4Ar1sDYpTV8BsaHfGUj2WXobhI"  # Токен Telegram-бота

# Инициализация бота
try:
    bot = Bot(token=TOKEN)
    logger.info("Бот инициализирован")
except Exception as e:
    logger.error(f"Ошибка инициализации бота: {e}")
    sys.exit(1)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    try:
        user_id = str(message.from_user.id)
        logger.info(f"Получена команда /start от user_id={user_id}")
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(text="Пополнить", url="https://yoomoney.ru"))
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

# Обработчик команды /help
@dp.message_handler(commands=['help'])
async def help_command(message: types.Message):
    try:
        user_id = str(message.from_user.id)
        logger.info(f"Получена команда /help от user_id={user_id}")
        help_text = (
            "Доступные команды:\n"
            "/start - Начать и получить ссылку на оплату\n"
            "/help - Показать эту помощь\n"
            "/info - Информация о боте"
        )
        await message.answer(help_text)
        logger.info(f"Отправлен ответ на /help для user_id={user_id}")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /help: {e}")
        await message.answer("Произошла ошибка, попробуйте позже.")

# Обработчик команды /info
@dp.message_handler(commands=['info'])
async def info_command(message: types.Message):
    try:
        user_id = str(message.from_user.id)
        logger.info(f"Получена команда /info от user_id={user_id}")
        info_text = "Это бот для подписки на канал 'Мой кайф'. Используйте /start для оплаты."
        await message.answer(info_text)
        logger.info(f"Отправлен ответ на /info для user_id={user_id}")
    except Exception as e:
        logger.error(f"Ошибка в обработчике /info: {e}")
        await message.answer("Произошла ошибка, попробуйте позже.")

# Запуск бота
def on_startup(_):
    logger.info("Бот запущен")

if __name__ == "__main__":
    try:
        logger.info("Запуск polling")
        executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
    except Exception as e:
        logger.error(f"Ошибка запуска polling: {e}")
        sys.exit(1)
