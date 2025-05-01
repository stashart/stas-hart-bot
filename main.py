import os
import telebot
from flask import Flask, request
import openai
import speech_recognition as sr
from pydub import AudioSegment

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
CREATOR_ID = 414284170  # Твой Telegram ID
memory_core = "memory_core.txt"
questions_log = "logs/questions.txt"
raw_log = "logs/raw.txt"

bot = telebot.TeleBot(API_TOKEN)
openai.api_key = OPENAI_API_KEY
app = Flask(__name__)

def append_to_file(filepath, text):
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(text + "\n")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        ogg_path = f"voice/{message.voice.file_id}.ogg"
        wav_path = f"voice/{message.voice.file_id}.wav"
        with open(ogg_path, 'wb') as f:
            f.write(downloaded_file)
        AudioSegment.from_file(ogg_path).export(wav_path, format="wav")
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="ru-RU")
        handle_all_messages(message, text=text)
    except Exception as e:
        bot.reply_to(message, "Не удалось распознать голос. Попробуй ещё раз.")
        print(f"Voice error: {e}")

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message, text=None):
    if not text:
        text = message.text
    append_to_file(raw_log, f"{message.from_user.id}: {text}")
    if message.from_user.id == CREATOR_ID:
        append_to_file(memory_core, text)
        append_to_file(questions_log, f"Q: {text}")

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
                {"role": "user", "content": text}
            ],
            max_tokens=400,
            temperature=0.8
        )
        reply = response.choices[0].message.content
        bot.reply_to(message, reply)
    except Exception as e:
        bot.reply_to(message, "Что-то пошло не так. Попробуй позже.")
        print(f"OpenAI error: {e}")

@app.route(f'/{API_TOKEN}', methods=["POST"])
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
