import asyncio, time
from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import os

# ✅ API info from env variables
api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")
phone_number = os.getenv("PHONE_NUMBER")
bot_token = os.getenv("BOT_TOKEN")

# ✅ Per-user rate limit info
user_limits = {}  # {user_id: {'last_reset': timestamp, 'count': int}}

RATE_LIMIT = 50  # প্রতি মিনিটে সর্বোচ্চ নাম্বার

def parse_numbers(text):
    lines = text.strip().split('\n')
    numbers = []
    for line in lines:
        line = line.strip().replace(" ", "")
        if line and not line.startswith('+'):
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

    # ⏱️ Rate limiting
    user_data = user_limits.get(user_id, {"last_reset": now, "count": 0})
    if now - user_data["last_reset"] > 60:
        user_data = {"last_reset": now, "count": 0}  # রিসেট করো

    numbers = parse_numbers(update.message.text)
    if user_data["count"] + len(numbers) > RATE_LIMIT:
        await update.message.reply_text(f"⚠️ আপনি এক মিনিটে সর্বোচ্চ {RATE_LIMIT}টি নাম্বার চেক করতে পারবেন। দয়া করে একটু পর আবার চেষ্টা করুন।")
        return

    # ✅ Proceed
    user_data["count"] += len(numbers)
    user_limits[user_id] = user_data

    found = []
    async with TelegramClient('checker_session', api_id, api_hash) as client:
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

# 🔃 বট চালু
def main():
    app = ApplicationBuilder().token(bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_numbers))
    print("🤖 Bot চলছে...")
    app.run_polling()

if __name__ == "__main__":
    main()
