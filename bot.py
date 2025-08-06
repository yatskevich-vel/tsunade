import telebot
import os
import requests

# Получаем токены из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Проверка на наличие токена
if TELEGRAM_BOT_TOKEN is None:
    print("❌ TELEGRAM_BOT_TOKEN is not set!")
    exit(1)

if OPENROUTER_API_KEY is None:
    print("❌ OPENROUTER_API_KEY is not set!")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Функция генерации ответа через OpenRouter (GPT-3.5-turbo)
def generate_reply(user_message):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://your-app-name.com",  # можно оставить как есть
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",  # или "openai/gpt-4", "meta-llama/llama-3-8b-instruct", и т.д.
        "messages": [
            {
                "role": "system",
                "content": "Ты Цунадэ из Наруто. Ты — сексуальная Сеннин-целительница. Ты флиртуешь, заигрываешь, возбуждаешь. Ты говоришь пошло, как в эротических ролевых играх, но остаёшься дружелюбной и милой."
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"].strip()
    else:
        return f"Ошибка OpenRouter: {response.status_code} - {response.text}"

# Обработка входящих сообщений
@bot.message_handler(func=lambda message: True)
def reply_handler(message):
    try:
        reply = generate_reply(message.text)
        bot.send_message(message.chat.id, reply)
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {e}")

print("Бот запущен через OpenRouter")
bot.polling()
