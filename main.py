# === Импорты и инициализация библиотек ===
import os
import time
import openai
import telebot
from flask import Flask, request
import subprocess
from deepgram import Deepgram  # 🎤 Deepgram SDK v2
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

    log_raw(user_id, user_input)                # 📝 Логируем

    if is_creator_or_channel(user_id, chat_id): # 📌 Если сообщение от Стаса или канала
        save_to_memory(user_input)
        if user_id == CREATOR_ID:
            log_question(user_input)           # 📚 Сохраняем вопрос

        try:
            memory = read_memory()             # 🧠 Читаем память
            reply_text = ask_openai(user_input, memory)  # 🤖 Ответ от GPT
            bot.reply_to(message, reply_text)  # 🔁 Ответ пользователю
        except Exception:
            if user_id == CREATOR_ID:
                bot.reply_to(message, "⚠️ Что-то пошло не так. Попробуй позже 🙃")

# === Обработка голосовых сообщений ===

# 🎙️ Асинхронная функция расшифровки аудио через Deepgram v2
async def transcribe_voice(file_path):
    dg = Deepgram(DEEPGRAM_API_KEY)
    with open(file_path, 'rb') as audio:
        source = {'buffer': audio, 'mimetype': 'audio/ogg'}
        options = {
            'language': 'ru',
            'punctuate': True,
            'model': 'general'
        }
        response = await dg.transcription.prerecorded(source, options)
        return response['results']['channels'][0]['alternatives'][0]['transcript']

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    try:
        user_id = message.from_user.id if message.from_user else CREATOR_ID
        chat_id = message.chat.id

        file_info = bot.get_file(message.voice.file_id)
        file = bot.download_file(file_info.file_path)

        ogg_path = f"voice/{message.voice.file_id}.ogg"
        with open(ogg_path, 'wb') as f:
            f.write(file)

        # 🔁 Расшифровка через Deepgram SDK v2
        user_input = asyncio.run(transcribe_voice(ogg_path))

        # 📌 Вся остальная логика остаётся:
        log_raw(user_id, user_input)

        if is_creator_or_channel(user_id, chat_id):
            save_to_memory(user_input)
            if user_id == CREATOR_ID:
                log_question(user_input)

            memory = read_memory()
            reply_text = ask_openai(user_input, memory)
            bot.reply_to(message, reply_text)

    except Exception as e:
        print(f"Ошибка при обработке голосового:\n{traceback.format_exc()}")
        if 'user_id' in locals() and user_id == CREATOR_ID:
            bot.reply_to(message, f"⚠️ Не получилось обработать голосовое\n{e}")

# === Webhook и просмотр памяти ===
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    print("📩 Пришёл webhook от Telegram")  # 🔍 Показываем, что Telegram стучится
    bot.process_new_updates([
        telebot.types.Update.de_json(request.stream.read().decode("utf-8"))  # 🔄 Обработка апдейтов
    ])
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    bot.remove_webhook()  # ❌ Удаляем старый webhook
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")  # 🔗 Устанавливаем новый
    return "Webhook установлен", 200

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
        return f"Размер памяти:\nCore: {core_size} байт\nBackup: {backup_size} байт", 200  # 📏 Размер файлов
    except Exception as e:
        return f"Ошибка при получении размера: {e}", 500

# === Восстановление памяти при запуске ===
try:
    if not os.path.exists("memory_core.txt") or os.stat("memory_core.txt").st_size == 0:
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            with open("memory_core.txt", "w", encoding="utf-8") as core:
                core.write(backup.read())     # 🔁 Восстановление из резервной копии
        print("🔁 Восстановлена память из memory_backup.txt")
    else:
        print("✅ Память уже есть, восстановление не требуется")
except Exception as e:
    print(f"⚠️ Ошибка при восстановлении памяти: {e}")

# === Запуск Flask-сервера ===
if __name__ == "__main__":
    try:
        print("🔧 Принудительно переустанавливаю webhook...")
        bot.remove_webhook()
        bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
        print("✅ Webhook установлен вручную")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

    if os.path.exists("memory_core.txt"):
        print("Файл memory_core.txt найден. Размер:", os.path.getsize("memory_core.txt"), "байт")
    else:
        print("⚠️ Файл memory_core.txt не найден!")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)        # 🚀 Запуск Flask-приложения
