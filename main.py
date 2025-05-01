@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_input = message.text.strip()

    # Сохраняем в общий лог
    with open("logs/raw.txt", "a", encoding="utf-8") as f:
        f.write(user_input + "\n")

    # Если в сообщении есть слово 'запомни', добавляем в память
    if "запомни" in user_input.lower():
        with open("memory_core.txt", "a", encoding="utf-8") as f:
            f.write(user_input + "\n")
        bot.reply_to(message, "Запомнил 🔒")
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
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt + "\n\n" + memory},
                {"role": "user", "content": user_input}
            ],
            max_tokens=400,
            temperature=0.8
        )

        reply = response.choices[0].message.content
        bot.reply_to(message, reply)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")
        print(f"Ошибка OpenAI: {e}")
