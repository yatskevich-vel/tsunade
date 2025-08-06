import os
import telebot
import requests
import flask 
from dotenv import load_dotenv
from flask import Flask, request
from collections import deque

print("Flask module:", flask)
print("Flask version:", flask.__version__)
print("before_first_request attr:", hasattr(flask.Flask, 'before_first_request'))

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, https://your-app.up.railway.app/webhook

if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY or not WEBHOOK_URL:
    raise ValueError("❌ Missing required env vars: TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, WEBHOOK_URL")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# 🧠 Память на пользователя
user_histories = {}

# 🔧 Prompt
system_prompt = {
    "role": "system",
    "content": (
        "Ты — Цунадэ Сэндзю, легендарная куноичи из мира Наруто, Пятая Хокаге Конохи..."
    )
}

# 🔗 Запрос к OpenRouter
def ask_openrouter(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yatskevich-vel/tsunade.git"
    }
    data = {
        "model": "openchat/openchat-3.5-0106",
        "messages": [system_prompt] + messages,
        "temperature": 0.9
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# 👂 Обработка входящих апдейтов Telegram
@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    return "", 403

# 🧠 Команды
@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.chat.id
    user_histories[user_id] = deque(maxlen=10)
    bot.send_message(user_id, "Привет, милый! Я Цунадэ, Пятая Хокаге... 😉")

@bot.message_handler(commands=["reset"])
def handle_reset(message):
    user_histories[message.chat.id] = deque(maxlen=10)
    bot.send_message(message.chat.id, "Хорошо, начнём с чистого листа... 💋")

@bot.message_handler(commands=["lore"])
def handle_lore(message):
    bot.send_message(message.chat.id, "Ты в мире Наруто. Цунадэ — Пятая Хокаге... 😉")

@bot.message_handler(commands=["roleplay"])
def handle_roleplay(message):
    bot.send_message(message.chat.id, "Представь: тёплый вечер... Что ты скажешь ей первым делом? 😘")

@bot.message_handler(commands=["hot"])
def handle_hot(message):
    bot.send_message(message.chat.id, "Хочешь перейти на более горячий уровень? 🔥")

# 💬 Главный диалог
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
        print(f"❌ Error: {e}")
        bot.send_message(user_id, "Что-то пошло не так. Попробуй снова позже 😢")

# 🔁 Устанавливаем Webhook при запуске
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# 🚀 Запуск Flask-приложения
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
