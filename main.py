import os
import openai
import telebot
from flask import Flask, request

# Загружаем токены
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CREATOR_ID = int(os.getenv("CREATOR_ID", "414284170"))  # Telegram ID Стаса

# Настройка
bot = telebot.TeleBot(API_TOKEN)
openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

@bot.message_handler(content_types=['text'])
def handle_message(message):
    user_input = message.text.strip()
    user_id = message.from_user.id

    # Логируем всё
    with open("logs/raw.txt", "a", encoding="utf-8") as f:
        f.write(f"{user_id}: {user_input}\n")

    # Только Стаса запоминаем и отвечаем
    if user_id == CREATOR_ID:
        # Память
        with open("memory_core.txt", "a", encoding="utf-8") as f:
            f.write(user_input + "\n")

        # Лог вопросов
        with open("logs/questions.txt", "a", encoding="utf-8") as f:
            f.write(user_input + "\n")

        try:
            print("Чтение памяти...")  # Лог перед чтением
            with open("memory_core.txt", "r", encoding="utf-8") as f:
                memory = f.read()

            print("Запрос к OpenAI...")  # Лог перед вызовом
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

            reply_text = response.choices[0].message["content"]
            print(f"Ответ OpenAI: {reply_text}")  # Лог ответа
            bot.reply_to(message, reply_text)

        except Exception as e:
            print(f"Ошибка при обращении к OpenAI: {e}")  # Лог ошибки
            bot.reply_to(message, "Что-то пошло не так. Попробуй позже 🙃")

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

# Просмотр памяти только для Стаса
@app.route("/memory", methods=["GET"])
def view_memory():
    token = request.args.get("key")
    if token != str(CREATOR_ID):
        return "Доступ запрещён 🙅", 403
    try:
        with open("memory_core.txt", "r", encoding="utf-8") as f:
            content = f.read()
        return f"<pre>{content}</pre>", 200
    except Exception as e:
        return f"Ошибка чтения памяти: {e}", 500

# Запуск
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
    
