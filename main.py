import os
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telethon.sync import TelegramClient
from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest
from telethon.tl.types import InputPhoneContact

# ✅ Load environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
PHONE_NUMBER = os.getenv("PHONE_NUMBER")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# ✅ Flask app init
app = Flask(__name__)

# ✅ Telegram Bot App
application = Application.builder().token(BOT_TOKEN).build()

# ✅ Telethon client
client = TelegramClient("anon", API_ID, API_HASH)

# ✅ Rate limit dict {user_id: [timestamps]}
user_rate_limit = {}

MAX_PER_MINUTE = 50  # Limit per minute

# ✅ /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 নমস্কার! নাম্বার দিন, আমি চেক করে বলব টেলিগ্রাম আছে কিনা।\n\nফরম্যাট:\n8801234567890\n8801987654321")

# ✅ Handle number list
async def check_numbers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = asyncio.get_event_loop().time()

    timestamps = user_rate_limit.get(user_id, [])
    timestamps = [t for t in timestamps if now - t < 60]

    lines = update.message.text.strip().splitlines()
    allowed = MAX_PER_MINUTE - len(timestamps)
    to_check = lines[:allowed]

    if not to_check:
        await update.message.reply_text("⚠️ প্রতি মিনিটে সর্বোচ্চ ৫০টি নাম্বার চেক করা যাবে। দয়া করে অপেক্ষা করুন।")
        return

    user_rate_limit[user_id] = timestamps + [now] * len(to_check)

    results = []
    await client.connect()

    if not await client.is_user_authorized():
        try:
            await client.send_code_request(PHONE_NUMBER)
            await client.sign_in(PHONE_NUMBER, input("Enter the code sent to Telegram: "))
        except Exception as e:
            await update.message.reply_text("❌ লগইন করতে সমস্যা হয়েছে।")
            return

    contacts = [InputPhoneContact(client_id=i, phone=number, first_name="User", last_name="") for i, number in enumerate(to_check)]
    try:
        result = await client(ImportContactsRequest(contacts))
        found = {user.phone: user for user in result.users}

        for number in to_check:
            if number in found:
                results.append(f"✅ {number} → Telegram আছে")
            else:
                results.append(f"❌ {number} → Telegram নেই")
    except Exception as e:
        await update.message.reply_text(f"⚠️ ত্রুটি: {str(e)}")
        return
    finally:
        await client(DeleteContactsRequest(contacts))

    reply = "\n".join(results)
    await update.message.reply_text(reply)

# ✅ Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_numbers))

# ✅ Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "OK"

# ✅ Health check
@app.route("/ping")
def ping():
    return "✅ Bot is live!"

# ✅ Setup Webhook
async def setup_webhook():
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")

# ✅ Start app with gunicorn
if __name__ == "__main__":
    print("🚀 Flask server শুরু হচ্ছে...")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_webhook())
    print("✅ Webhook সেট হয়েছে! 🤖 Bot চালু হয়েছে!")
    app.run(host="0.0.0.0", port=10000)
