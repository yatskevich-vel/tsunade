import os
import telebot
import requests
from dotenv import load_dotenv
from collections import deque

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN or OPENROUTER_API_KEY is not set!")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# 🧹 Удалим Webhook при старте
requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook")

# 🔁 Polling
if __name__ == "__main__":
    print("🚀 Bot started")
    bot.infinity_polling()

# Память диалога на пользователя
user_histories = {}

# Базовый system prompt
system_prompt = {
    "role": "system",
    "content": (
        "Ты — Цунадэ Сэндзю, легендарная куноичи из мира Наруто, Пятая Хокаге Конохи. "
        "Ты умна, властна, сексуальна и уверена в себе. Ты обращаешься к собеседнику как к дорогому, привлекательному гостю. "
        "Ты находишься в Конохе, но можешь представить любую эротическую фантазию. "
        "Ты ведёшь флирт, эротический диалог, возбуждающе описываешь сцены и задаёшь вопросы. "
        "Все события — игра воображения, основанная на ролевом взаимодействии."
    )
}

# Запрос к OpenRouter
def ask_openrouter(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yatskevich-vel/tsunade.git"  # Укажи ссылку на свой репозиторий
    }
    data = {
        "model": "openchat/openchat-3.5-0106",
        "messages": [system_prompt] + messages,
        "temperature": 0.9
    }

    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Команды
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.chat.id
    user_histories[user_id] = deque(maxlen=10)
    bot.send_message(user_id, "Привет, милый! Я Цунадэ, Пятая Хокаге... Ты ведь не просто так пришёл ко мне? 😉")

@bot.message_handler(commands=["reset"])
def handle_reset(message):
    user_id = message.chat.id
    user_histories[user_id] = deque(maxlen=10)
    bot.send_message(user_id, "Хорошо, начнём с чистого листа... 💋")

@bot.message_handler(commands=["lore"])
def handle_lore(message):
    bot.send_message(message.chat.id, "Ты находишься в мире Наруто. Цунадэ — Пятая Хокаге, но любит развлекаться в свободное время. Может быть, ты шиноби или странник, попавший в Коноху... 😉")

@bot.message_handler(commands=["roleplay"])
def handle_roleplay(message):
    bot.send_message(message.chat.id, "Представь: тёплый вечер, горячие источники... Цунадэ ждет тебя в уединённой купальне. Что ты скажешь ей первым делом? 😘")

@bot.message_handler(commands=["hot"])
def handle_hot(message):
    bot.send_message(message.chat.id, "Хочешь перейти на более горячий уровень, да? Только скажи, и я сделаю всё, чтобы ты не забыл эту ночь... 🔥")

# Основной диалог
@bot.message_handler(func=lambda message: True)
def chat(message):
    user_id = message.chat.id
    user_input = message.text

    if user_id not in user_histories:
        user_histories[user_id] = deque(maxlen=10)

    history = user_histories[user_id]
    history.append({"role": "user", "content": user_input})

    try:
        reply = ask_openrouter(list(history))
        history.append({"role": "assistant", "content": reply})
        bot.send_message(user_id, reply)
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(user_id, "Что-то пошло не так. Попробуй снова позже 😢")

print("Bot started.")
bot.infinity_polling()
