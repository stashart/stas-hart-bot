import os
import openai
import telebot
from flask import Flask, request

# Загружаем токены
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Настраиваем бота и OpenAI
bot = telebot.TeleBot(API_TOKEN)
openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

# Обработка сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Можно заменить на gpt-4
            messages=[
                {"role": "system", "content": "Ты — Стас, осознанный инвестор, духовный человек, который отвечает спокойно, с наблюдением и юмором."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=400,
            temperature=0.8
        )

        reply = response['choices'][0]['message']['content']
        bot.reply_to(message, reply)

    except Exception as e:
        bot.reply_to(message, "Что-то пошло не так. Попробуй позже.")
        print(f"Ошибка OpenAI: {e}")

# Вебхук от Telegram
@app.route(f"/{API_TOKEN}", methods=["POST"])
def receive_update():
    bot.process_new_updates([
        telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    ])
    return "ok", 200

# Установка вебхука
@app.route("/", methods=["GET"])
def set_webhook():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
    return "Webhook установлен", 200

# Запуск Flask-приложения
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
