import os
import time
import openai
import telebot
from flask import Flask, request
import subprocess

try:
    result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("🎉 ffmpeg найден:\n", result.stdout.decode())
except FileNotFoundError:
    print("❌ ffmpeg НЕ установлен")

# Загружаем токены
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CREATOR_ID = int(os.getenv("CREATOR_ID", "414284170"))  # Telegram ID Стаса
CHANNEL_ID = -1001889831695  # ID канала @stasnastavnik

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

    # Запоминаем, если это Стас или канал
    if user_id == CREATOR_ID or chat_id == CHANNEL_ID:
        print("Файл существует:", os.path.exists("memory_core.txt"))
        print("Размер файла:", os.path.getsize("memory_core.txt"), "байт")

        with open("memory_core.txt", "a", encoding="utf-8") as f:
            f.write(user_input + "\n")

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

            if user_id == CREATOR_ID:
                bot.reply_to(message, reply_text)

        except Exception as e:
            print(f"Ошибка при обращении к OpenAI: {e}")
            if user_id == CREATOR_ID:
                bot.reply_to(message, "Что-то пошло не так. Попробуй позже 🙃")

# ===== ОБРАБОТКА ГОЛОСОВЫХ =====

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id

        print("📥 Голосовое сообщение получено")

        # Скачиваем файл
        file_info = bot.get_file(message.voice.file_id)
        file = bot.download_file(file_info.file_path)

        ogg_path = f"voice/{message.voice.file_id}.ogg"
        wav_path = f"voice/{message.voice.file_id}.wav"

        os.makedirs("voice", exist_ok=True)
        with open(ogg_path, 'wb') as f:
            f.write(file)

        # Конвертация в WAV через ffmpeg
        from pydub import AudioSegment
        AudioSegment.from_file(ogg_path).export(wav_path, format="wav")

        # Отправка в Whisper
        with open(wav_path, "rb") as audio_file:
            transcript = openai.Audio.transcribe("whisper-1", audio_file)

        user_input = transcript["text"]
        print(f"🗣️ Расшифровка: {user_input}")

        # Дальше — как с обычным текстом
        with open("logs/raw.txt", "a", encoding="utf-8") as f:
            f.write(f"{user_id}: {user_input}\n")

        if user_id == CREATOR_ID or chat_id == CHANNEL_ID:
            with open("memory_core.txt", "a", encoding="utf-8") as f:
                f.write(user_input + "\n")

            if user_id == CREATOR_ID:
                with open("logs/questions.txt", "a", encoding="utf-8") as f:
                    f.write(user_input + "\n")

        # Запрос к OpenAI
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            backup_data = backup.read()
        with open("memory_core.txt", "r", encoding="utf-8") as core:
            core_data = core.read()
        memory = backup_data + "\n" + core_data

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
        print("🎤 Ответ на голосовое:", reply_text)

        if user_id == CREATOR_ID:
            bot.reply_to(message, reply_text)

    except Exception as e:
        print(f"Ошибка при обработке голосового: {e}")
        if user_id == CREATOR_ID:
            bot.reply_to(message, "⚠️ Не получилось обработать голосовое")
            
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

# 📍 Запуск
if __name__ == "__main__":
    try:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
        print("✅ Webhook установлен автоматически")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

    print("🔎 Проверка памяти при запуске")
    print("Файл memory_core.txt существует:", os.path.exists("memory_core.txt"))
    if os.path.exists("memory_core.txt"):
        print("Размер:", os.path.getsize("memory_core.txt"), "байт")
    else:
        print("Файл не найден!")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
