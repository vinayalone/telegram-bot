import sqlite3
import asyncio
import logging
from telegram import Update
from telegram.error import NetworkError, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ChatJoinRequestHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# 🔴 PUT YOUR BOT TOKEN HERE
BOT_TOKEN = "8501256382:AAFljrs50mfkR-wge0zeyQjEtKNDKpUdABM"

# 🔐 ADMIN ID
ADMIN_ID = 5422522348

# ---------- LOGGING ----------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------- DATABASE ----------
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)"
)
db.commit()


def save_user(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,),
    )
    db.commit()


# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_user.id
    save_user(user_id)

    try:
        await update.message.reply_text(
            "Hello 👋\n\n"
            "This bot is used for promotion.\n"
            "Contact admin for details."
        )
    except NetworkError:
        print("⚠️ Network issue while replying /start")


# ---------- JOIN REQUEST ----------
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    save_user(user.id)

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=(
                "Thanks for requesting to join 🔥\n\n"
                "For promotion or details, contact admin."
            ),
        )
    except NetworkError:
        print("⚠️ Network issue while sending join message")


# ---------- BROADCAST COMMAND ----------
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data["broadcast"] = True
    await update.message.reply_text(
        "📢 Send the message you want to broadcast to all users."
    )


# ---------- BROADCAST MESSAGE ----------
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("broadcast"):
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent = 0
    for (user_id,) in users:
        try:
            await update.message.copy(chat_id=user_id)
            sent += 1
            await asyncio.sleep(0.05)  # ✅ prevents disconnect
        except TelegramError:
            continue

    context.user_data["broadcast"] = False
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users.")


# ---------- ERROR HANDLER ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    if isinstance(context.error, NetworkError):
        print("⚠️ Network error occurred. Telegram unreachable.")
    else:
        print(f"❌ Unexpected error: {context.error}")


# ---------- MAIN ----------
def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(MessageHandler(filters.ALL, handle_broadcast))

    app.add_error_handler(error_handler)

    print("Bot is running...")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()
