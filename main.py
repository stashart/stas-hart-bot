import os
import openai
import telebot
from flask import Flask, request

# Загружаем токены
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Настройка
bot = telebot.TeleBot(API_TOKEN)
openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

# Обработка сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text.strip()

    # Сохраняем в общий лог
    with open("logs/raw.txt", "a", encoding="utf-8") as f:
        f.write(user_input + "\n")

    # Запоминаем по слову "запомни"
    if "запомни" in user_input.lower():
        with open("memory_core.txt", "a", encoding="utf-8") as f:
            f.write(user_input + "\n")
        bot.reply_to(message, "Запомнил 🧠")
        return

    # Логируем вопросы
    with open("logs/questions.txt", "a", encoding="utf-8") as f:
        f.write(user_input + "\n")

    try:
        with open("memory_core.txt", "r", encoding="utf-8") as f:
            memory = f.read()

        system_prompt = (
            "Ты — Хартия. Цифровой голос Стаса. Говори как он: с уверенностью, наблюдением, лёгким юмором.\n"
            "Используй накопленную память, чтобы помогать и подсказывать."
        )

        response = openai.ChatCompletion.create(
            model="gpt-4-0613",
            messages=[
                {"role": "system", "content": system_prompt + "\n\n" + memory},
                {"role": "user", "content": user_input}
            ],
            max_tokens=400,
            temperature=0.8
        )

        bot.reply_to(message, response.choices[0].message["content"])

    except Exception as e:
        bot.reply_to(message, "Что-то пошло не так. Попробуй позже 🙃")
        print(f"Ошибка OpenAI: {e}")

# Webhook
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
    return "Webhook установлен", 200

# Запуск Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
