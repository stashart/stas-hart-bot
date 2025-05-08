# === Импорты и инициализация библиотек ===
import os
import time
import openai
import telebot
from flask import Flask, request
import subprocess
from deepgram import DeepgramClient, FileSource, PrerecordedOptions  # 🎤 Deepgram SDK v4
import asyncio                  # ⏱ async обработка

# === Константы и Инициализация переменных среды ===

API_TOKEN = os.getenv("TELEGRAM_TOKEN")              # 🔑 Токен Telegram-бота
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")         # 🔑 API ключ OpenAI
WEBHOOK_URL = os.getenv("WEBHOOK_URL")               # 🌐 Webhook URL
CREATOR_ID = int(os.getenv("CREATOR_ID", "414284170"))  # 👤 ID Стаса
CHANNEL_ID = -1001889831695                           # 📣 ID канала @stasnastavnik
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")     # 🔑 Ключ Deepgram

# === Инициализация библиотек ===

bot = telebot.TeleBot(API_TOKEN)                      # 🤖 Telegram-бот
openai.api_key = OPENAI_API_KEY                       # 🧠 Ключ OpenAI
app = Flask(__name__)                                 # 🚀 Flask-приложение
os.makedirs("logs", exist_ok=True)                    # 📁 Папка логов
os.makedirs("voice", exist_ok=True)                   # 🎤 Папка для голосовых

# === Проверка ffmpeg ===

if subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE).returncode == 0:
    print("🎉 ffmpeg найден")
else:
    print("❌ ffmpeg НЕ установлен")

# === Утилиты и вспомогательные функции ===

def is_creator_or_channel(user_id, chat_id):
    return user_id == CREATOR_ID or chat_id == CHANNEL_ID

def read_memory():
    try:
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            backup_data = backup.read()
        with open("memory_core.txt", "r", encoding="utf-8") as core:
            core_data = core.read()
        return backup_data + "\n" + core_data
    except:
        return ""

def log_raw(user_id, text):
    with open("logs/raw.txt", "a", encoding="utf-8") as f:
        f.write(f"{user_id}: {text}\n")

def log_question(text):
    with open("logs/questions.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")

def save_to_memory(text):
    with open("memory_core.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")

def ask_openai(user_input, memory):
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
    return response.choices[0].message["content"]

# === Обработка текстовых сообщений ===

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_input = message.text.strip()
    user_id = message.from_user.id
    chat_id = message.chat.id

    log_raw(user_id, user_input)  # 📝 Логируем

    if is_creator_or_channel(user_id, chat_id):  # 📌 Если сообщение от Стаса или канала
        save_to_memory(user_input)
        if user_id == CREATOR_ID:
            log_question(user_input)  # 📚 Сохраняем вопрос

        try:
            memory = read_memory()  # 🧠 Читаем память
            reply_text = ask_openai(user_input, memory)  # 🤖 Ответ от GPT
            bot.reply_to(message, reply_text)  # 🔁 Ответ пользователю
        except Exception as e:
            import traceback
            print("❌ Ошибка при обработке текстового сообщения:")
            print(traceback.format_exc())
            if user_id == CREATOR_ID:
                bot.reply_to(message, "⚠️ Что-то пошло не так. Попробуй позже 🙃")

# ─── Debug-ловец — сразу после создания bot ───

@bot.message_handler(func=lambda m: True)
def debug_all_messages(message):
    print("📨 Debug all — content_type =", message.content_type)
    # раскомментируйте, чтобы увидеть весь объект:
    # print(message)

# === Обработка голосовых сообщений ===

# 🎙️ Синхронная функция расшифровки аудио через Deepgram v4

def transcribe_voice(file_path: str) -> str:
    dg = DeepgramClient(DEEPGRAM_API_KEY)

    # Читаем аудио в буфер
    with open(file_path, 'rb') as audio_file:
        source = FileSource(
            buffer=audio_file.read(),
            mimetype="audio/ogg; codecs=opus"
        )
    # Опции: модель можно менять на "nova", "general" и т.д.
    options = PrerecordedOptions(
        model="nova",
        language="ru",
        punctuate=True
    )

    # Синхронный запрос
    response = dg.transcription.prerecorded(source=source, options=options)
    # Берём распознанный текст
    transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
    return transcript
    
@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice(message):
    print("📥 Голосовое или аудиосообщение получено")

    try:
        # Определяем ID пользователя
        user_id = message.from_user.id if message.from_user else CREATOR_ID
        chat_id = message.chat.id
        print(f"👤 user_id: {user_id}, chat_id: {chat_id}")

        # Проверяем, что есть voice или audio
        if message.voice:
            file_id = message.voice.file_id
            print("🎙️ Тип: voice")
        elif message.audio:
            file_id = message.audio.file_id
            print("🎵 Тип: audio")
        else:
            print("❌ Нет подходящего voice/audio файла")
            return

        # Получаем файл и сохраняем
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)
        print("📁 Файл скачан с Telegram")

        ogg_path = f"voice/{file_id}.ogg"
        with open(ogg_path, 'wb') as f:
            f.write(file)
        print("✅ Файл сохранён локально:", ogg_path)

        # Расшифровка
        print("🔄 Отправляем в Deepgram для расшифровки...")
        user_input = transcribe_voice(ogg_path)
        print("🗣️ Расшифровка получена:", user_input)

        # Логирование
        log_raw(user_id, user_input)

        if is_creator_or_channel(user_id, chat_id):
            save_to_memory(user_input)
            print("📌 Записано в память")
            if user_id == CREATOR_ID:
                log_question(user_input)
                print("📚 Сохранён вопрос")

        # Отвечаем без вызова OpenAI
        if user_id == CREATOR_ID:
            bot.reply_to(message, "✅ Голосовое получено и добавлено в память")

    except Exception as e:
        print("❌ Ошибка при обработке голосового:\n", traceback.format_exc())
        if 'user_id' in locals() and user_id == CREATOR_ID:
            bot.reply_to(message, f"⚠️ Не получилось обработать голосовое\n{e}")

# === Webhook и просмотр памяти ===

@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    print("📩 Пришёл webhook от Telegram")  # 🔍 Показываем, что Telegram стучится
    raw_update = request.stream.read().decode("utf-8")
    print("🌀 RAW UPDATE:", raw_update)
    update = telebot.types.Update.de_json(raw_update)
    bot.process_new_updates([update])  # 🔄 Обработка апдейтов
    return "ok", 200

# === Health check endpoint ===
@app.route("/", methods=["GET"])
def index():
    return "Service is running", 200  # 🟢 Simple health check

# === Memory endpoints ===
@app.route("/memory", methods=["GET"])
def view_memory():
    token = request.args.get("key")
    if token != str(CREATOR_ID):
        return "Доступ запрещён 🙅", 403
    try:
        memory = read_memory()
        return f"<pre>{memory}</pre>", 200  # 📖 Показываем память в HTML
    except Exception as e:
        return f"Ошибка чтения памяти: {e}", 500

@app.route("/memory-size", methods=["GET"])
def memory_size():
    try:
        core_size = os.path.getsize("memory_core.txt")
        backup_size = os.path.getsize("memory_backup.txt")
        return (
            f"Размер памяти:\nCore: {core_size} байт\n"
            f"Backup: {backup_size} байт"
        ), 200  # 📏 Размер файлов
    except Exception as e:
        return f"Ошибка при получении размера: {e}", 500

# === Восстановление памяти при запуске ===
try:
    if not os.path.exists("memory_core.txt") or os.stat("memory_core.txt").st_size == 0:
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            data = backup.read()
        with open("memory_core.txt", "w", encoding="utf-8") as core:
            core.write(data)  # 🔁 Восстановление из резервной копии
        print("🔁 Восстановлена память из memory_backup.txt")
    else:
        print("✅ Память уже есть, восстановление не требуется")
except Exception as e:
    print(f"⚠️ Ошибка при восстановлении памяти: {e}")

# === Автоматическая установка webhook и запуск сервера ===
if __name__ == "__main__":
    # 🗑️ Удаляем старый webhook
    try:
        bot.remove_webhook()
        print("🗑️ Старый webhook удалён")
    except Exception as e:
        print(f"❌ Ошибка при удалении webhook: {e}")

    # 🔗 Устанавливаем новый webhook
    try:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
        print("✅ Webhook установлен автоматически:", f"{WEBHOOK_URL}/{API_TOKEN}")
    except Exception as e:
        print(f"❌ Ошибка при установке webhook: {e}")

    # 🚀 Запуск Flask-приложения
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
