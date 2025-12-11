import logging
import requests
import json
import time
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТОКЕНЫ из environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GIGACHAT_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY")
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")

logging.basicConfig(level=logging.INFO)

user_data = {}

QUESTIONS = [
    "1. Какова ваша основная цель использования продукта/услуги?",
    "2. Какие проблемы вы хотите решить?",
    "3. Каков ваш бюджет на решение?",
    "4. Какой у вас опыт работы с подобными продуктами?",
    "5. Как быстро вам нужно решение?",
    "6. Какие функции для вас наиболее важны?",
    "7. Что может повлиять на ваше решение о покупке?"
]

def get_gigachat_access_token():
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        "Authorization": f"Basic {GIGACHAT_AUTH_KEY}",
        "RqUID": f"{int(time.time() * 1000)}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"scope": "GIGACHAT_API_PERS"}
    try:
        response = requests.post(url, headers=headers, data=data, verify=False)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        logging.error(f"Ошибка получения токена: {e}")
        return None

def analyze_with_gigachat(answers):
    access_token = get_gigachat_access_token()
    if not access_token:
        return "Ошибка подключения к GigaChat"
    
    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""Проанализируй ответы клиента и создай 5 персональных профилей (персон) для воронки продаж.

Ответы клиента:
{chr(10).join([f"{q}: {a}" for q, a in zip(QUESTIONS, answers)])}

Для каждой персоны выведи:
- **Имя персоны**
- **Описание** (2-3 предложения)
- **Боли и потребности**
- **Мотивация к покупке**
- **Возражения**

Формат вывода - структурированный список из 5 персон."""
    
    payload = {
        "model": "GigaChat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, verify=False)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"Ошибка анализа GigaChat: {e}")
        return f"Ошибка анализа: {str(e)}"

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data[user_id] = {"answers": [], "question_index": 0}
    await update.message.reply_text(
        "👋 Привет! Я помогу определить твою целевую аудиторию.\n\n"
        "Ответь на 7 вопросов, и я создам для тебя 5 персональных профилей клиентов.\n\n"
        f"{QUESTIONS[0]}"
    )

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_data:
        await update.message.reply_text("Нажми /start чтобы начать")
        return
    
    data = user_data[user_id]
    data["answers"].append(update.message.text)
    data["question_index"] += 1
    
    if data["question_index"] < len(QUESTIONS):
        await update.message.reply_text(QUESTIONS[data["question_index"]])
    else:
        await update.message.reply_text("⏳ Анализирую твои ответы с помощью GigaChat AI...")
        analysis = analyze_with_gigachat(data["answers"])
        await update.message.reply_text(f"✅ **Результаты анализа:**\n\n{analysis}")
        del user_data[user_id]

def main():
    print("🤖 Бот запущен и ожидает сообщений...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))
    
    app.run_polling()

if __name__ == '__main__':
    main()
