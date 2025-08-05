import telebot
from openai import OpenAI
import os

# Токены
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)

# Функция генерации ответа
def generate_reply(user_message):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # или gpt-4, если доступен
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

print("Бот запущен")
bot.polling()
