import os                   # Работа с переменными окружения, путями и файлами
import time                 # Для задержек, замеров времени
import openai               # Подключение к OpenAI API (GPT)
import telebot              # Библиотека для работы с Telegram-ботом (pyTelegramBotAPI)
from flask import Flask, request  # Flask нужен для запуска webhook-сервера
import subprocess           # Для вызова команд системы (например, ffmpeg)
from deepgram import Deepgram  # SDK Deepgram для обработки голосовых

# Проверка наличия ffmpeg (нужно для работы с аудиофайлами)
try:
    result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    print("🎉 ffmpeg найден:\n", result.stdout.decode())
except FileNotFoundError:
    print("❌ ffmpeg НЕ установлен")

# Загружаем токены из переменных окружения
API_TOKEN = os.getenv("TELEGRAM_TOKEN")              # Токен Telegram-бота
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")         # Ключ API OpenAI
WEBHOOK_URL = os.getenv("WEBHOOK_URL")               # URL для webhook (если используется Flask)
CREATOR_ID = int(os.getenv("CREATOR_ID", "414284170"))  # Telegram ID Стаса (по умолчанию)
CHANNEL_ID = -1001889831695  # Telegram ID канала @stasnastavnik

# Deepgram
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")     # Ключ Deepgram API
if not DEEPGRAM_API_KEY:
    print("❌ Не найден DEEPGRAM_API_KEY в переменных окружения!")
else:
    print("🔑 Deepgram API key загружен (первые 5 символов):", DEEPGRAM_API_KEY[:5])

# Настройка бота и Flask-сервера
bot = telebot.TeleBot(API_TOKEN)                     # Инициализация Telegram-бота
openai.api_key = OPENAI_API_KEY                      # Установка ключа OpenAI
app = Flask(__name__)                                # Инициализация Flask-приложения

# ===== ОБРАБОТКА ТЕКСТОВЫХ СМС =====

@bot.message_handler(content_types=['text'])  # Обработчик текстовых сообщений
def handle_message(message):
    user_input = message.text.strip()         # Удаляем лишние пробелы из текста сообщения
    user_id = message.from_user.id            # ID пользователя, отправившего сообщение
    chat_id = message.chat.id                 # ID чата (может быть группой, каналом или личкой)

    # Логируем всё в файл logs/raw.txt
    with open("logs/raw.txt", "a", encoding="utf-8") as f:
        f.write(f"{user_id}: {user_input}\n")  # Сохраняем в формате: [user_id]: [сообщение]

    # Запоминаем сообщение, если оно от Стаса или из канала
    if user_id == CREATOR_ID or chat_id == CHANNEL_ID:
        print("Файл существует:", os.path.exists("memory_core.txt"))              # Проверка, есть ли файл памяти
        print("Размер файла:", os.path.getsize("memory_core.txt"), "байт")        # Вывод размера файла памяти

        with open("memory_core.txt", "a", encoding="utf-8") as f:
            f.write(user_input + "\n")                                            # Добавляем сообщение в память

        if user_id == CREATOR_ID:
            with open("logs/questions.txt", "a", encoding="utf-8") as f:
                f.write(user_input + "\n")                                        # Логируем вопрос Стаса отдельно

        try:
            print("Чтение памяти...")                                             # Загружаем backup и core память
            with open("memory_backup.txt", "r", encoding="utf-8") as backup:
                backup_data = backup.read()
            with open("memory_core.txt", "r", encoding="utf-8") as core:
                core_data = core.read()

            memory = backup_data + "\n" + core_data                               # Объединяем память
            print("🔁 Используем: backup + core")
            print(f"🔢 Размер памяти: {len(memory)} символов")

            start_time = time.time()                                              # Засекаем время генерации

            print("Запрос к OpenAI...")
            system_prompt = (
                "Ты — Хартия. Цифровой голос Стаса. Говори как он: с уверенностью, наблюдением, лёгким юмором.\n"
                "Используй накопленную память, чтобы помогать и подсказывать."
            )

            response = openai.ChatCompletion.create(                              # Запрос к GPT-4 с памятью
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
                bot.reply_to(message, reply_text)                                 # Отвечаем только Стасу (личка)

        except Exception as e:
            import traceback
            print(f"Ошибка при обращении к OpenAI:\n{traceback.format_exc()}")    # Ошибка GPT-запроса
            if user_id == CREATOR_ID:
                bot.reply_to(message, "⚠️ Что-то пошло не так. Попробуй позже 🙃")  # Ответ об ошибке только Стасу

# ===== ОБРАБОТКА ГОЛОСОВЫХ =====

@bot.message_handler(content_types=['voice'])  # Обработчик голосовых сообщений
def handle_voice(message):
    try:
        user_id = message.from_user.id if message.from_user else CREATOR_ID  # ID отправителя
        chat_id = message.chat.id

        print("📥 Голосовое сообщение получено")

        # Скачиваем голосовое сообщение с Telegram
        file_info = bot.get_file(message.voice.file_id)         # Получаем информацию о файле
        file = bot.download_file(file_info.file_path)           # Скачиваем файл

        ogg_path = f"voice/{message.voice.file_id}.ogg"         # Путь для сохранения файла
        os.makedirs("voice", exist_ok=True)                     # Создаём папку voice, если её нет
        with open(ogg_path, 'wb') as f:
            f.write(file)                                       # Сохраняем .ogg-файл локально

        # Deepgram SDK v3 — синхронная расшифровка
        api_key = os.getenv("DEEPGRAM_API_KEY")                 # Получаем ключ из переменных среды
        dg = DeepgramClient(api_key)                            # Инициализируем клиента Deepgram

        with open(ogg_path, 'rb') as audio:                     # Открываем .ogg-файл
            source: FileSource = {
                "buffer": audio,
                "mimetype": "audio/ogg; codecs=opus"            # Указываем формат OGG с кодеком Opus
            }
            options: PrerecordedOptions = {
                "model": "nova",                                # Используем модель Nova (лучшая)
                "language": "ru"                                # Русский язык распознавания
            }
            response = dg.listen.prerecorded.transcribe_file(
                source=source,
                options=options
            )

        # Извлекаем текст из результата
        user_input = response["results"]["channels"][0]["alternatives"][0].get("transcript", "").strip()
        if not user_input:
            raise ValueError("Пустая расшифровка от Deepgram")

        print(f"🗣️ Расшифровка (Deepgram): {user_input}")

        # Логируем текст, полученный из голосового
        with open("logs/raw.txt", "a", encoding="utf-8") as f:
            f.write(f"{user_id}: {user_input}\n")  # Сохраняем в лог

        # Запоминаем, если это Стас или канал
        if user_id == CREATOR_ID or chat_id == CHANNEL_ID:
            print("📌 Запись в память:", user_input)
            with open("memory_core.txt", "a", encoding="utf-8") as f:
                f.write(user_input + "\n")         # Добавляем в основную память
            if user_id == CREATOR_ID:
                with open("logs/questions.txt", "a", encoding="utf-8") as f:
                    f.write(user_input + "\n")     # Логируем отдельно вопросы Стаса

        # Читаем backup и основную память
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            backup_data = backup.read()
        with open("memory_core.txt", "r", encoding="utf-8") as core:
            core_data = core.read()
        memory = backup_data + "\n" + core_data     # Объединяем

        # Запрос к OpenAI (GPT-4)
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
            bot.reply_to(message, reply_text)       # Отвечаем только Стасу

    except Exception as e:
        import traceback
        error_text = traceback.format_exc()
        print(f"Ошибка при обработке голосового:\n{error_text}")
        if 'user_id' in locals() and user_id == CREATOR_ID:
            bot.reply_to(message, "⚠️ Не получилось обработать голосовое\n" + str(e))
            
# Webhook обработка (Telegram будет слать POST-запросы сюда)
@app.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([
        telebot.types.Update.de_json(request.stream.read().decode("utf-8"))  # Декодируем обновление из запроса
    ])
    return "ok", 200  # Telegram ждёт ответ 200 OK

# Установка webhook (через GET-запрос по корню "/")
@app.route("/", methods=["GET"])
def index():
    bot.remove_webhook()  # Удаляем старый webhook
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")  # Устанавливаем новый webhook
    return "Webhook установлен", 200

# Просмотр содержимого памяти (только для Стаса)
@app.route("/memory", methods=["GET"])
def view_memory():
    token = request.args.get("key")  # Проверка доступа по Telegram ID
    if token != str(CREATOR_ID):
        return "Доступ запрещён 🙅", 403
    try:
        with open("memory_backup.txt", "r", encoding="utf-8") as backup:
            backup_data = backup.read()
        with open("memory_core.txt", "r", encoding="utf-8") as core:
            core_data = core.read()
        return f"<pre>{backup_data + '\n' + core_data}</pre>", 200  # Возвращаем память в HTML формате
    except Exception as e:
        return f"Ошибка чтения памяти: {e}", 500

# Просмотр размера файлов памяти
@app.route("/memory-size", methods=["GET"])
def memory_size():
    try:
        core_size = os.path.getsize("memory_core.txt")      # Размер core файла
        backup_size = os.path.getsize("memory_backup.txt")  # Размер backup файла
        return f"Размер памяти:\nCore: {core_size} байт\nBackup: {backup_size} байт", 200
    except Exception as e:
        return f"Ошибка при получении размера: {e}", 500

# 🧠 Восстановление памяти из backup, если основной файл пустой или отсутствует
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

# 📍 Точка входа — запуск Flask-приложения
if __name__ == "__main__":
    try:
        bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")  # Ставим webhook при запуске
        print("✅ Webhook установлен автоматически")
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")

    print("🔎 Проверка памяти при запуске")
    if os.path.exists("memory_core.txt"):
        print("Файл memory_core.txt найден. Размер:", os.path.getsize("memory_core.txt"), "байт")
    else:
        print("⚠️ Файл memory_core.txt не найден!")

    port = int(os.environ.get("PORT", 5000))       # Чтение порта (например, для Heroku)
    app.run(host="0.0.0.0", port=port)             # Запуск Flask-сервера
