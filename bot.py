import telebot
from openai import OpenAI
import os

# Получаем переменные из Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Проверка токенов (можно убрать после отладки)
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в переменных окружения")
if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY не найден в переменных окружения")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# Генерация ответа
def generate_reply(user_message):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": "Ты Цунадэ из Наруто. Ты — сексуальная Сеннин-целительница. Ты флиртуешь, заигрываешь, возбуждаешь. Ты говоришь пошло, как в эротических ролевых играх, но остаёшься дружелюбной и милой."
            },
            {
                "role": "user",
                "content": user_message
            }
        ],
        temperature=0.95
    )
    return response.choices[0].message.content.strip()

# Обработка сообщений
@bot.message_handler(func=lambda message: True)
def reply_handler(message):
    try:
        reply = generate_reply(message.text)
        bot.send_message(message.chat.id, reply)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

print("🤖 Бот запущен")
bot.polling()
