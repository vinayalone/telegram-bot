import os
import sqlite3
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ChatJoinRequestHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5422522348

logging.basicConfig(level=logging.INFO)

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
    save_user(update.effective_user.id)
    await update.message.reply_text(
        "Hello 👋\n\nThis bot is used for promotion.\nContact admin for details."
    )


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
    except TelegramError:
        pass


# ---------- ADMIN PANEL ----------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Total Users", callback_data="count")],
    ]

    await update.message.reply_text(
        "🛠 Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- CALLBACK HANDLER ----------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "count":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        await query.message.reply_text(
            f"👥 Total users: {total}"
        )

    elif query.data == "broadcast":
        context.user_data["broadcast"] = True
        await query.message.reply_text(
            "📢 Send the message you want to broadcast.\n\n"
            "It will be sent to all users."
        )


# ---------- HANDLE BROADCAST ----------
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
            await asyncio.sleep(0.05)  # rate limit safety
        except TelegramError:
            continue

    context.user_data["broadcast"] = False
    await update.message.reply_text(
        f"✅ Broadcast sent to {sent} users."
    )


# ---------- MAIN ----------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.ALL, handle_broadcast))

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
