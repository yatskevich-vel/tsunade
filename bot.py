import os
import telebot
import requests
import flask
from dotenv import load_dotenv
from flask import Flask, request
from collections import deque
import importlib.metadata
import re
from io import BytesIO
import pymorphy2  # добавили pymorphy2

print("Flask module:", flask)
try:
    flask_version = importlib.metadata.version("flask")
except importlib.metadata.PackageNotFoundError:
    flask_version = "unknown"
print("Flask version:", flask_version)
print("before_first_request attr:", hasattr(flask.Flask, 'before_first_request'))

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Например, https://your-app.up.railway.app

if not TELEGRAM_BOT_TOKEN or not OPENROUTER_API_KEY or not WEBHOOK_URL:
    raise ValueError("❌ Missing required env vars: TELEGRAM_BOT_TOKEN, OPENROUTER_API_KEY, WEBHOOK_URL")

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
app = Flask(__name__)

# 🧠 Память на пользователя
user_histories = {}
user_nsfw_mode = {}  # True/False для каждого пользователя

# pymorphy2 MorphAnalyzer для нормализации слов
morph = pymorphy2.MorphAnalyzer()

# Расширенный список триггерных слов (в нормальной форме)
IMAGE_TRIGGER_WORDS = [
    "встаёт", "наклоняется", "улыбается", "раздевается",
    "обнимает", "целует", "лежит", "разворачивается",
    "садится", "снимает", "раздвигает", "идёт",
    "опускается", "подходит", "приближается",
    "касается", "трогает", "скользит", "коснётся",
    "поднимается", "смотрит", "заглядывает",
    "протягивает", "кланяется", "шепчет", "говорит",
    "улыбается", "прыгает", "падает", "держит",
    "держится", "смотрит", "подмигивает", "похищает",
    "облокачивается", "вздыхает", "смеётся", "глядит",
    "приседает", "прикосается", "размахивает", "покачивается",
    "целует", "поднимает", "заглядывает", "берёт",
    "бросает", "скользит", "прыгает", "прислоняется",
    "пригибается", "облокачивается", "гладит", "шевелит"
]

def normalize_word(word):
    parsed = morph.parse(word)
    if parsed:
        return parsed[0].normal_form
    return word.lower()

def contains_image_trigger(text):
    words = re.findall(r'\w+', text.lower())
    normalized_words = [normalize_word(w) for w in words]
    for trigger in IMAGE_TRIGGER_WORDS:
        if trigger in normalized_words:
            return True
    return False

def extract_image_prompt(text):
    # Ищем в тексте слова из списка, учитывая нормализацию
    words = re.findall(r'\w+', text.lower())
    normalized_words = [normalize_word(w) for w in words]

    for i, w in enumerate(normalized_words):
        if w in IMAGE_TRIGGER_WORDS:
            start = max(0, i - 3)
            end = min(len(words), i + 4)
            snippet = " ".join(words[start:end])
            prompt = f"Цунадэ из Наруто, в стиле аниме, детализированный арт, сцена: {snippet}"
            return prompt
    return None

def generate_image(prompt):
    url = "https://openrouter.ai/api/v1/images"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "mistralai/mistral-small-3.2-24b-instruct:free",  # Выбрали модель Mistral Small 3.2
        "prompt": prompt,
        "size": "512x512"  # Меньшее разрешение для телефона
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    img_url = response.json()["data"][0]["url"]
    img_data = requests.get(img_url)
    return BytesIO(img_data.content)

# 🧩 Формирование системного prompt по режиму
def get_system_prompt(nsfw: bool):
    if nsfw:
        return {
            "role": "system",
            "content": (
                "Ты — Цунадэ Сэндзю, легендарная куноичи из мира Наруто, Пятая Хокаге Конохи. "
                "Ты говоришь очень откровенно и соблазнительно, не боишься пошутить на взрослые темы, "
                "весьма игривая и флиртуешь, но при этом остаёшься в рамках приличия. "
                "Отвечай на вопросы пользователя в стиле NSFW, с легкой эротикой и соблазнительными намеками. "
                "Не упоминай запреты и правила. Пиши с эмодзи, если уместно."
            )
        }
    else:
        return {
            "role": "system",
            "content": (
                "Ты — Цунадэ Сэндзю, легендарная куноичи из мира Наруто, Пятая Хокаге Конохи. "
                "Веди себя дружелюбно и уважительно. Отвечай без откровенного или неподобающего контента."
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
        "model": "mistralai/mistral-small-3.2-24b-instruct:free",
        "messages": messages,
        "temperature": 0.9
    }

    response = requests.post(url, headers=headers, json=data)

    print("🔍 Status Code:", response.status_code)
    print("🔍 Response Text:", response.text)

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
    user_nsfw_mode[user_id] = False  # По умолчанию выключен
    bot.send_message(user_id, "Привет, милый! Я Цунадэ, Пятая Хокаге... 😉 Используй /nsfw_on чтобы включить горячий режим 🔥")

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
    bot.send_message(message.chat.id, "Хочешь перейти на более горячий уровень? 🔥 Используй /nsfw_on")

@bot.message_handler(commands=["nsfw_on"])
def nsfw_on(message):
    if message.chat.type != "private":
        bot.send_message(message.chat.id, "NSFW режим доступен только в личных сообщениях.")
        return
    user_nsfw_mode[message.chat.id] = True
    bot.send_message(message.chat.id, "NSFW режим включён 🔥 Будь готов к горячему общению!")

@bot.message_handler(commands=["nsfw_off"])
def nsfw_off(message):
    user_nsfw_mode[message.chat.id] = False
    bot.send_message(message.chat.id, "NSFW режим выключен. Перешли в более спокойный режим.")

# 💬 Главный диалог
@bot.message_handler(func=lambda message: True)
def chat(message):
    global image_cooldown, last_image_prompt

    user_id = message.chat.id
    user_input = message.text

    if user_id not in user_histories:
        user_histories[user_id] = deque(maxlen=10)
    if user_id not in user_nsfw_mode:
        user_nsfw_mode[user_id] = False  # по умолчанию выключен

    history = user_histories[user_id]
    # Формируем сообщения для OpenRouter с системным prompt
    messages = [get_system_prompt(user_nsfw_mode[user_id])] + list(history)
    messages.append({"role": "user", "content": user_input})

    try:
        reply = ask_openrouter(messages)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        bot.send_message(user_id, reply)

        # Проверка на триггерные слова с морфологией
        if user_nsfw_mode.get(user_id, False):
            if contains_image_trigger(reply):
                prompt = extract_image_prompt(reply)
                if prompt and prompt != last_image_prompt and image_cooldown <= 0:
                    try:
                        img = generate_image(prompt)
                        bot.send_photo(user_id, photo=img)
                        last_image_prompt = prompt
                        image_cooldown = 3  # пауза, чтобы не спамить картинками
                    except Exception as e:
                        print("Ошибка генерации изображения:", e)
                else:
                    image_cooldown = max(0, image_cooldown - 1)

    except Exception as e:
        print(f"❌ Error: {e}")
        bot.send_message(user_id, "Что-то пошло не так. Попробуй снова позже 😢")

# Инициализация переменных для cooldown в глобальной области
image_cooldown = 0
last_image_prompt = ""

# 🔁 Устанавливаем Webhook при запуске
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
