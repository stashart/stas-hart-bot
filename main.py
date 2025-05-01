import os
import telebot
import openai
from flask import Flask, request

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CREATOR_ID = 414284170

bot = telebot.TeleBot(API_TOKEN)
openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

memory_core = "memory_core.txt"
questions_log = "logs/questions.txt"
raw_log = "logs/raw.txt"

def append_to_file(filename, text):
    with open(filename, "a", encoding="utf-8") as f:
        f.write(text.strip() + "\n")

def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text

    if user_id == CREATOR_ID:
        append_to_file(raw_log, f"Стас: {text}")
        append_to_file(questions_log, text)
        append_to_file(memory_core, text)

    with open(memory_core, "r", encoding="utf-8") as f:
        memory_data = f.read()

    system_prompt = (
        "Ты — Хартия. Цифровой голос Стаса. Говори с глубиной, уверенностью, юмором и наблюдением. "
        "Иногда подстёбывай, если уместно. Ни в коем случае не выдавай себя за ассистента или помощника. "
        "Ты — как внутренний голос Стаса, но отвечаешь всем, кто пишет."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt + "\n\n" + memory_data},
                {"role": "user", "content": text},
            ],
            max_tokens=400,
            temperature=0.8
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "Что-то пошло не так. Попробуй позже.")
        print(f"Ошибка OpenAI: {e}")

@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([
        telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    ])
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
    return "Webhook установлен", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
