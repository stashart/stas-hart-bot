from flask import Flask, request
import telebot
import os

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@app.route('/' + API_TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url=os.getenv("WEBHOOK_URL") + API_TOKEN)
    return "!", 200

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я работаю на Railway.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
