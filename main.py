import os
import openai
import telebot
from flask import Flask, request
from datetime import datetime
import json
import uuid

# Токены и ключи
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CREATOR_ID = int(os.getenv("CREATOR_ID"))

# Пути к файлам
memory_core = "memory_core.txt"
questions_log = "logs/questions.txt"
raw_log = "logs/raw.txt"

bot = telebot.TeleBot(API_TOKEN)
openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

# Сохраняем сообщение в файл
def append_to_file(path, text):
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")

# Обработка сообщений
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text.strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Логируем всё
    raw_entry = f"[{timestamp}] {user_name} ({user_id}): {text}"
    append_to_file(raw_log, raw_entry)

    # Только сообщения от создателя запоминаются
    if user_id == CREATOR_ID:
        append_to_file(questions_log, text)
        append_to_file(memory_core, f"{user_name}: {text}")

    # Генерируем ответ
    try:
        with open(memory_core, "r", encoding="utf-8") as f:
            memory_data = f.read()

        system_prompt = (
            "Ты — Хартия. Цифровой голос Стаса. Говори с глубиной, уверенностью, юмором и наблюдением.\n"
            "Иногда подстёбывай, если уместно. Не выдавай себя за ассистента или помощника.\n"
            "Ты — как внутренний голос Стаса, но отвечаешь всем, кто пишет."
        )

        response = openai.ChatCompletion.create(
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
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([
        telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    ])
    return "ok", 200

# Установка вебхука
@app.route("/", methods=["GET"])
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
    return "Webhook установлен", 200

# Запуск Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
