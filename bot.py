import os
import re
import requests
from flask import Flask, request
from openai import OpenAI
from io import BytesIO

app = Flask(__name__)

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_TEXT = "cognitivecomputations/dolphin-mistral-24b-venice-edition:free"
MODEL_IMAGE = "stabilityai/stable-diffusion-xl"

# Telegram API URL
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# Слова-триггеры для генерации картинки
IMAGE_TRIGGERS = [
    "встала", "наклонилась", "улыбнулась", "разделась",
    "обняла", "поцеловала", "села", "легла", "посмотрела"
]

# Счётчик сообщений, чтобы не генерировать картинки слишком часто
message_counter = 0
last_image_message_id = None
IMAGE_COOLDOWN = 3  # каждые 3 сообщения

def send_message(chat_id, text):
    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

def send_photo(chat_id, image_bytes):
    files = {"photo": BytesIO(image_bytes)}
    files["photo"].name = "image.png"
    requests.post(f"{TELEGRAM_URL}/sendPhoto", data={"chat_id": chat_id}, files=files)

def generate_text(prompt):
    response = client.chat.completions.create(
        model=MODEL_TEXT,
        messages=[
            {"role": "system", "content": "Ты Цунадэ из аниме, отвечай в NSFW-стиле."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

def generate_image(prompt):
    img_response = client.images.generate(
        model=MODEL_IMAGE,
        prompt=prompt,
        size="512x512"
    )
    image_url = img_response.data[0].url
    img_data = requests.get(image_url).content
    return img_data

def contains_trigger(text):
    return any(trigger in text.lower() for trigger in IMAGE_TRIGGERS)

@app.route("/", methods=["POST"])
def webhook():
    global message_counter, last_image_message_id

    data = request.json
    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if not chat_id or not text:
        return "ok"

    # Генерация ответа
    reply_text = generate_text(text)
    send_message(chat_id, reply_text)

    # Логика автогенерации картинки
    message_counter += 1
    if contains_trigger(reply_text) and (last_image_message_id is None or message_counter - last_image_message_id >= IMAGE_COOLDOWN):
        img_data = generate_image(reply_text)
        send_photo(chat_id, img_data)
        last_image_message_id = message_counter

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
