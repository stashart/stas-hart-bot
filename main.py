import os
import time
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
    chat_id = message.chat.id

    # Логируем всё
    with open("logs/raw.txt", "a", encoding="utf-8") as f:
        f.write(f"{user_id}: {user_input}\n")

    # Запоминаем, если это Стас или канал @stasnastavnik
    if user_id == CREATOR_ID or chat_id == -1001889831695:
        with open("memory_core.txt", "a", encoding="utf-8") as f:
            f.write(user_input + "\n")

        # Только если пишет Стас — логируем как вопрос
        if user_id == CREATOR_ID:
            with open("logs/questions.txt", "a", encoding="utf-8") as f:
                f.write(user_input + "\n")

        try:
            print("Чтение памяти...")

            with open("memory_backup.txt", "r", encoding="utf-8") as backup:
                backup_data = backup.read()
            with open("memory_core.txt", "r", encoding="utf-8") as core:
                core_data = core.read()

            memory = backup_data + "\n" + core_data

            print("🔁 Используем: backup + core")
            print(f"🔢 Размер памяти: {len(memory)} символов")

            start_time = time.time()

            print("Запрос к OpenAI...")
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

            elapsed = time.time() - start_time
            reply_text = response.choices[0].message["content"]
            print(f"Ответ OpenAI: {reply_text}")
            print(f"⏱️ Время генерации: {elapsed:.2f} сек")

            # Отвечаем только Стасу
            if user_id == CREATOR_ID:
                bot.reply_to(message, reply_text)

        except Exception as e:
            print(f"Ошибка при обращении к OpenAI: {e}")
            if user_id == CREATOR_ID:
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

# Просмотр памяти
@app.route("/memory", methods=["GET"])
def view_memory():
    token = request.args.get("key")
    if token != str(CREATOR_ID):
        return "Доступ запрещён 🙅", 403
    try:
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            backup_data = backup.read()
        with open("memory_core.txt", "r", encoding="utf-8") as core:
            core_data = core.read()
        full_memory = backup_data + "\n" + core_data
        return f"<pre>{full_memory}</pre>", 200
    except Exception as e:
        return f"Ошибка чтения памяти: {e}", 500

# Просмотр размера памяти
@app.route("/memory-size", methods=["GET"])
def memory_size():
    try:
        core_size = os.path.getsize("memory_core.txt")
        backup_size = os.path.getsize("memory_backup.txt")
        return f"Размер памяти:\nCore: {core_size} байт\nBackup: {backup_size} байт", 200
    except Exception as e:
        return f"Ошибка при получении размера: {e}", 500

# 🧠 Восстановление core из backup при запуске
try:
    if not os.path.exists("memory_core.txt") or os.stat("memory_core.txt").st_size == 0:
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            backup_data = backup.read()
        with open("memory_core.txt", "w", encoding="utf-8") as f:
            f.write(backup_data)
        print("🔁 Восстановлена память из memory_backup.txt")
    else:
        print("✅ Память уже есть, восстановление не требуется")
except Exception as e:
    print(f"⚠️ Ошибка при восстановлении памяти: {e}")

# Запуск
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
