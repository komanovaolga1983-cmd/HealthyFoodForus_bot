import os
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# ------------------- Конфигурация -------------------
# Токены берём из переменных окружения, чтобы не светить в коде.
# При локальном запуске можно временно вписать их прямо в код,
# но в облаке обязательно используйте переменные окружения.
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# ------------------- Загрузка меню из JSON -------------------
# Меню хранится в отдельном файле menu.json
try:
    with open("menu.json", "r", encoding="utf-8") as f:
        MENU = json.load(f)
    logger.info("Меню загружено успешно")
except Exception as e:
    logger.error(f"Ошибка загрузки меню: {e}")
    MENU = {}

# ------------------- Системный промпт для Groq -------------------
SYSTEM_PROMPT = """
Ты — персональный диетолог и шеф-повар, работающий по принципу Гарвардской тарелки.
Твои рекомендации должны быть:
- полезными и сбалансированными,
- использовать недорогие продукты, доступные в магазинах «Перекрёсток» и «Магнит»,
- рецепты быстрыми и простыми в приготовлении,
- рассчитаны на 2 порции.
Если пользователь просит заменить продукт — предлагай равноценную по пользе и доступности альтернативу.
Отвечай дружелюбно, кратко, в стиле заботливого консультанта.
"""

# ------------------- Функции для работы с Groq -------------------
async def ask_groq(user_message: str) -> str:
    """Отправляет запрос в Groq и возвращает ответ."""
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            model="llama-3.3-70b-versatile",   # быстрая и умная модель
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка Groq: {e}")
        return "Извините, сейчас я не могу обратиться к своему ИИ-мозгу. Попробуйте позже."

# ------------------- Обработчики команд -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍽️ Привет! Я ваш умный помощник по Гарвардской тарелке.\n\n"
        "🎯 Я могу:\n"
        "/menu — меню на сегодня\n"
        "/day <N> — меню на день N (например, /day 3)\n"
        "/shopping — список покупок на сегодня\n"
        "/dessert — рецепт быстрого десерта дня\n\n"
        "🤖 А ещё вы можете спросить меня словами:\n"
        "«Чем заменить курицу?» или «Предложи лёгкий ужин из трёх ингредиентов»"
    )

async def menu_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = "1"  # в реальном проекте можно привязать к дате
    data = MENU.get(day)
    if not data:
        await update.message.reply_text("Меню на сегодня не найдено.")
        return
    text = (
        f"📅 День {day} (меню на двоих)\n"
        f"☀️ Завтрак: {data['breakfast']}\n"
        f"🌞 Обед: {data['lunch']}\n"
        f"🌙 Ужин: {data['dinner']}"
    )
    await update.message.reply_text(text)

async def day_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите номер дня: /day 5")
        return
    day = context.args[0]
    data = MENU.get(day)
    if not data:
        await update.message.reply_text(f"Меню для дня {day} не найдено.")
        return
    text = (
        f"📅 День {day} (на 2 персоны)\n"
        f"☀️ Завтрак: {data['breakfast']}\n"
        f"🌞 Обед: {data['lunch']}\n"
        f"🌙 Ужин: {data['dinner']}\n\n"
        f"🛒 Продукты: {', '.join(data['shopping'])}\n"
        f"🍰 Десерт: {data['dessert']}"
    )
    await update.message.reply_text(text)

async def shopping_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = "1"
    data = MENU.get(day)
    if not data:
        await update.message.reply_text("Список покупок отсутствует.")
        return
    products = "\n".join(f"• {item}" for item in data["shopping"])
    await update.message.reply_text(f"🛒 Продукты на день {day} (на двоих):\n{products}")

async def dessert_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    day = "1"
    data = MENU.get(day)
    if not data:
        await update.message.reply_text("Десерт не задан.")
        return
    await update.message.reply_text(f"🍰 Десерт дня:\n{data['dessert']}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает все текстовые сообщения, не являющиеся командами."""
    user_text = update.message.text
    # Показываем статус "печатает"
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    answer = await ask_groq(user_text)
    await update.message.reply_text(answer)

# ------------------- Запуск бота -------------------
def main():
    if not TELEGRAM_TOKEN or not GROQ_API_KEY:
        logger.critical("Не заданы TELEGRAM_TOKEN или GROQ_API_KEY. Проверьте переменные окружения.")
        exit(1)

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_today))
    app.add_handler(CommandHandler("day", day_menu))
    app.add_handler(CommandHandler("shopping", shopping_today))
    app.add_handler(CommandHandler("dessert", dessert_today))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()