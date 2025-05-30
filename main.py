import os
import time
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact

# 📦 Env variables
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")
phone_number = os.getenv("PHONE_NUMBER")
webhook_url = os.getenv("WEBHOOK_URL")  # eg: https://yourdomain.com/webhook

app = Flask(__name__)

# 🌐 Webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# 🛡️ Rate limiting
RATE_LIMIT = 50
user_limits = {}

def parse_numbers(text):
    lines = text.strip().split('\n')
    numbers = []
    for line in lines:
        line = line.strip().replace(" ", "")
        if line:
            if not line.startswith('+'):
                line = '+' + line
            numbers.append(line)
    return numbers

async def check_number(client, number):
    try:
        contact = InputPhoneContact(client_id=0, phone=number, first_name="Check", last_name="User")
        result = await client(ImportContactsRequest([contact]))
        user = result.users[0] if result.users else None

        if user:
            await client(DeleteContactsRequest(id=[user.id]))
            return True
    except:
        pass
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 হ্যালো! নাম্বার পাঠাও (এক লাইন-একটা করে), আমি চেক করব কার Telegram আছে।")

async def handle_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    now = time.time()

    user_data = user_limits.get(user_id, {"last_reset": now, "count": 0})
    if now - user_data["last_reset"] > 60:
        user_data = {"last_reset": now, "count": 0}

    numbers = parse_numbers(update.message.text)
    if user_data["count"] + len(numbers) > RATE_LIMIT:
        await update.message.reply_text(f"⚠️ প্রতি মিনিটে সর্বোচ্চ {RATE_LIMIT}টি নাম্বার চেক করা যাবে। একটু পর আবার চেষ্টা করুন।")
        return

    user_data["count"] += len(numbers)
    user_limits[user_id] = user_data

    found = []
    async with TelegramClient("checker_session", api_id, api_hash) as client:
        await client.start(phone=phone_number)
        for number in numbers:
            exists = await check_number(client, number)
            if exists:
                found.append(number)

    if found:
        reply = "✅ Telegram-এ আছে:\n" + '\n'.join(found)
    else:
        reply = "❌ কোনো নাম্বার Telegram-এ নেই।"

    await update.message.reply_text(reply)

# 🧠 অ্যাপ্লিকেশন সেটআপ
application = Application.builder().token(bot_token).concurrent_updates(True).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_numbers))

# 🔃 বটের Webhook শুরু
async def setup_webhook():
    await application.bot.set_webhook(f"{webhook_url}/webhook")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook())
    app.run(host="0.0.0.0", port=10000)  # Render: port 10000
