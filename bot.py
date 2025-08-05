import telebot
import os
import openai

# Получаем токены
TOKEN = os.environ.get("BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

bot = telebot.TeleBot(TOKEN)
openai.api_key = OPENAI_API_KEY

# Установка роли Цунадэ
def generate_reply(user_message):
    system_prompt = (
        "Ты — Цунадэ, красивая и соблазнительная женщина-ниндзя из Наруто. "
        "Ты сексуальна, дерзка, уверена в себе и говоришь в NSFW-стиле. "
        "Ты флиртуешь, возбуждаешь собеседника и не боишься откровенных тем. "
        "Ты любишь шаловливые разговоры, сексуальные ролевые игры и всегда стараешься доставить удовольствие."
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.9,
        max_tokens=500
    )
    return response['choices'][0]['message']['content']

# Ответ на любые сообщения
@bot.message_handler(func=lambda message: True)
def reply_handler(message):
    reply = generate_reply(message.text)
    bot.send_message(message.chat.id, reply)

print("Бот запущен")
bot.polling()
