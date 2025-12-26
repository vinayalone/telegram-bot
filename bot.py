import os
import sqlite3
import asyncio
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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
db = sqlite3.connect("bot.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute(
    "CREATE TABLE IF NOT EXISTS channels (channel_id INTEGER PRIMARY KEY, message TEXT)"
)
cursor.execute(
    """CREATE TABLE IF NOT EXISTS buttons (
        channel_id INTEGER,
        text TEXT,
        url TEXT,
        callback TEXT
    )"""
)
db.commit()


def save_user(user_id: int):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
    )
    db.commit()


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    await update.message.reply_text(
        "Hello 👋\n\nThis bot is used for promotion.\nContact admin for details."
    )


# ---------- JOIN REQUEST ----------
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    chat_id = update.chat_join_request.chat.id
    save_user(user.id)

    cursor.execute(
        "SELECT message FROM channels WHERE channel_id=?", (chat_id,)
    )
    row = cursor.fetchone()
    if not row:
        return

    cursor.execute(
        "SELECT text, url, callback FROM buttons WHERE channel_id=?", (chat_id,)
    )
    btns = cursor.fetchall()

    keyboard = []
    for text, url, callback in btns:
        if url:
            keyboard.append([InlineKeyboardButton(text, url=url)])
        else:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback)])

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=row[0],
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
        )
    except TelegramError:
        pass


# ---------- ADMIN PANEL ----------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [
        [InlineKeyboardButton("➕ Set Channel Message", callback_data="set_msg")],
        [InlineKeyboardButton("🔘 Set Buttons", callback_data="set_btn")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📊 User Count", callback_data="count")],
    ]

    await update.message.reply_text(
        "🛠 Admin Panel", reply_markup=InlineKeyboardMarkup(kb)
    )


# ---------- CALLBACKS ----------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "count":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        await q.message.reply_text(f"👥 Total users: {total}")

    elif q.data == "broadcast":
        context.user_data["broadcast"] = True
        await q.message.reply_text("Send message to broadcast.")


# ---------- BROADCAST ----------
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.user_data.get("broadcast"):
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for (uid,) in users:
        try:
            await update.message.copy(uid)
            await asyncio.sleep(0.05)
        except TelegramError:
            pass

    context.user_data["broadcast"] = False
    await update.message.reply_text("✅ Broadcast completed.")


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
