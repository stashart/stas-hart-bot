# -*- coding: utf-8 -*-
import os
from flask import Flask, request
import telebot
from openai import OpenAI
from datetime import datetime

# Настройка
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CREATOR_ID = 414284170  # Telegram ID Стаса

bot = telebot.TeleBot(API_TOKEN)
client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__)

# Подготовка директорий и файлов
os.makedirs("memory", exist_ok=True)
os.makedirs("voice", exist_ok=True)

memory_core = "memory/memory_core.txt"
questions_log = "memory/user_questions_log.txt"
raw_log = "memory/memory_raw_log.txt"

for file in [memory_core, questions_log, raw_log]:
    if not os.path.exists(file):
        open(file, "a", encoding="utf-8").close()

# Функция: сохранить в файл
def append_to_file(path, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {content}\n")

# Обработка всех текстов
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()
    username = message.from_user.username or "no_username"

    # Лог всего
    append_to_file(raw_log, f"{username} ({user_id}): {text}")

    # Разделение памяти
    if user_id == CREATOR_ID:
        append_to_file(memory_core, text)
    else:
        append_to_file(questions_log, f"{username}: {text}")

    # Формируем system prompt
    with open(memory_core, "r", encoding="utf-8") as f:
        memory_data = f.read()

    system_prompt = (
        "Ты — Хартия. Цифровой голос Стаса. Говори с глубиной, уверенностью, юмором и наблюдением. "
        "Иногда подстёбывай, если уместно. Ни в коем случае не выдавай себя за ассистента или помощника. "
        "Ты — как внутренний голос Стаса, но отвечаешь всем, кто пишет."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt + "\n\n" + memory_data},
                {"role": "user", "content": text}
            ],
            max_tokens=400,
            temperature=0.8
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "Что-то пошло не так. Попробуй позже.")
        print(f"Ошибка OpenAI: {e}")

# Webhook от Telegram
@app.route(f"/{API_TOKEN}", methods=['POST'])
def webhook():
    bot.process_new_updates([
        telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    ])
    return "ok", 200

@app.route("/", methods=['GET'])
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
    return "Webhook установлен", 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
