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
import pymorphy2  # морфологический анализатор

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

# Память на пользователя
user_histories = {}
user_nsfw_mode = {}  # True/False для каждого пользователя

# pymorphy2 MorphAnalyzer для нормализации слов
morph = pymorphy2.MorphAnalyzer()

# Список триггерных слов (в нормальной форме)
IMAGE_TRIGGER_WORDS = [
    # исходные три формы (наст., прош. ж.р., повелительное)
    "встаёт", "встала", "встань",
    "наклоняется", "наклонилась", "наклонись",
    "улыбается", "улыбнулась", "улыбнись",
    "раздевается", "разделась", "раздевайся",
    "обнимает", "обняла", "обними",
    "целует", "поцеловала", "поцелуй",
    "лежит", "лежала", "лежи",
    "разворачивается", "развернулась", "развернись",
    "садится", "села", "сядь",
    "снимает", "сняла", "сними",
    "раздвигает", "раздвинула", "раздвинь",
    "идёт", "шла", "иди",
    "опускается", "опустилась", "опустись",
    "подходит", "подошла", "подойди",
    "приближается", "приблизилась", "приблизься",
    "касается", "коснулась", "коснись",
    "трогает", "трогнула", "трогни",
    "скользит", "скользнула", "скользни",
    "поднимается", "поднялась", "поднимись",
    "смотрит", "посмотрела", "посмотри",
    "заглядывает", "заглянула", "загляни",
    "протягивает", "протянула", "протяни",
    "кланяется", "поклонилась", "поклонись",
    "шепчет", "прошептала", "прошепчи",
    "говорит", "сказала", "скажи",
    "прыгает", "прыгнула", "прыгни",
    "падает", "упала", "упади",
    "держит", "держала", "держи",
    "держится", "держалась", "держись",
    "подмигивает", "подмигнула", "подмигни",
    "похищает", "похитила", "похитись",
    "облокачивается", "облокотилась", "облокотись",
    "вздыхает", "вздохнула", "вздохни",
    "смеётся", "засмеялась", "засмейся",
    "глядит", "глянула", "глянь",
    "приседает", "присела", "присесть",
    "прикосается", "прикоснулась", "прикоснись",
    "размахивает", "размахнула", "размахни",
    "покачивается", "покачнулась", "покачнись",
    "поднимает", "подняла", "подними",
    "берёт", "взяла", "возьми",
    "бросает", "бросила", "брось",
    "прислоняется", "прислонилась", "прислонись",
    "пригибается", "пригнулась", "пригнись",
    "гладит", "погладила", "погладь",
    "шевелит", "пошевелила", "пошевели",

    # новые триггеры
    "моргает", "моргнула", "моргни",
    "кивает", "кивнула", "кивни",
    "улыбнулся", "улыбнулась", "улыбнись",
    "смеётся", "засмеялась", "засмейся",
    "закрывает глаза", "закрыла глаза", "закрой глаза",
    "открывает глаза", "открыла глаза", "открой глаза",
    "задумывается", "задумалась", "задумайся",
    "обнимается", "обнялась", "обнимись",
    "целуется", "поцеловалась", "поцелуйся",
    "тихо шепчет", "прошептала тихо", "прошепчи тихо",
    "поднимает бровь", "подняла бровь", "подними бровь",
    "задёргивается", "задёргалась", "задёргись",
    "танцует", "потанцевала", "потанцуй",
    "шелестит", "шелестнула", "шелестни",
    "провожает взглядом", "проводила взглядом", "провожай взглядом",
    "лирично улыбается", "лирично улыбнулась", "лирично улыбнись",

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
        "model": "meta-llama/llama-3.2-11b-vision-instruct:free",
        "prompt": prompt,
        "size": "512x512"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    img_url = response.json()["data"][0]["url"]
    img_data = requests.get(img_url)
    return BytesIO(img_data.content)

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

def ask_openrouter(messages):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yatskevich-vel/tsunade.git"
    }
    data = {
        "model": qwen/qwen3-coder:free",
        "messages": messages,
        "temperature": 0.9
    }

    response = requests.post(url, headers=headers, json=data)

    print("🔍 Status Code:", response.status_code)
    print("🔍 Response Text:", response.text)

    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

@app.route("/", methods=["POST"])
def webhook():
    if request.headers.get("content-type") == "application/json":
        json_string = request.get_data().decode("utf-8")
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "", 200
    return "", 403

@bot.message_handler(commands=["start"])
def handle_start(message):
    user_id = message.chat.id
    user_histories[user_id] = deque(maxlen=10)
    user_nsfw_mode[user_id] = False
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

@bot.message_handler(func=lambda message: True)
def chat(message):
    global image_cooldown, last_image_prompt

    user_id = message.chat.id
    user_input = message.text

    if user_id not in user_histories:
        user_histories[user_id] = deque(maxlen=10)
    if user_id not in user_nsfw_mode:
        user_nsfw_mode[user_id] = False

    history = user_histories[user_id]
    messages = [get_system_prompt(user_nsfw_mode[user_id])] + list(history)
    messages.append({"role": "user", "content": user_input})

    try:
        reply = ask_openrouter(messages)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})
        bot.send_message(user_id, reply)

        if user_nsfw_mode.get(user_id, False):
            if contains_image_trigger(user_input):  # <- заменено с reply на user_input
                prompt = extract_image_prompt(user_input)  # <- тоже с reply на user_input
                if prompt and prompt != last_image_prompt and image_cooldown <= 0:
                    try:
                        img = generate_image(prompt)
                        bot.send_photo(user_id, photo=img)
                        last_image_prompt = prompt
                        image_cooldown = 3
                    except Exception as e:
                        print("Ошибка генерации изображения:", e)
                else:
                    image_cooldown = max(0, image_cooldown - 1)

    except Exception as e:
        print(f"❌ Error: {e}")
        bot.send_message(user_id, "Что-то пошло не так. Попробуй снова позже 😢")

image_cooldown = 0
last_image_prompt = ""

if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
