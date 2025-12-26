import os
import sqlite3
import asyncio
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
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


def save_user(uid: int):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (uid,))
    db.commit()


# ---------- START ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)
    await update.message.reply_text("Hellow 👋\nBot is active.")


# ---------- JOIN REQUEST ----------
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    chat_id = update.chat_join_request.chat.id
    save_user(user.id)

    cursor.execute("SELECT message FROM channels WHERE channel_id=?", (chat_id,))
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

    await context.bot.send_message(
        chat_id=user.id,
        text=row[0],
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None,
    )


# ---------- ADMIN PANEL ----------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    kb = [
        [InlineKeyboardButton("📝 Set Channel Message", callback_data="set_msg")],
        [InlineKeyboardButton("🔘 Added Button", callback_data="add_btn")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📊 User Count", callback_data="count")],
    ]

    await update.message.reply_text(
        "🛠 Admin Panel", reply_markup=InlineKeyboardMarkup(kb)
    )


# ---------- CALLBACK HANDLER ----------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "count":
        cursor.execute("SELECT COUNT(*) FROM users")
        await q.message.reply_text(
            f"👥 Total users: {cursor.fetchone()[0]}"
        )

    elif q.data == "set_msg":
        context.user_data["step"] = "channel_id"
        await q.message.reply_text("Send CHANNEL ID")

    elif q.data == "add_btn":
        context.user_data["btn_step"] = "channel"
        await q.message.reply_text("Send CHANNEL ID for button")


# ---------- ADMIN TEXT FLOW ----------
async def admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    # SET CHANNEL MESSAGE
    if context.user_data.get("step") == "channel_id":
        context.user_data["channel_id"] = int(update.message.text)
        context.user_data["step"] = "message"
        await update.message.reply_text("Now send the message text")
        return

    if context.user_data.get("step") == "message":
        cid = context.user_data["channel_id"]
        cursor.execute(
            "INSERT OR REPLACE INTO channels VALUES (?, ?)",
            (cid, update.message.text),
        )
        db.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Channel message saved")
        return

    # ADD BUTTON
    if context.user_data.get("btn_step") == "channel":
        context.user_data["btn_channel"] = int(update.message.text)
        context.user_data["btn_step"] = "text"
        await update.message.reply_text("Send button TEXT")
        return

    if context.user_data.get("btn_step") == "text":
        context.user_data["btn_text"] = update.message.text
        context.user_data["btn_step"] = "url"
        await update.message.reply_text(
            "Send URL (or type CALLBACK)"
        )
        return

    if context.user_data.get("btn_step") == "url":
        cid = context.user_data["btn_channel"]
        text = context.user_data["btn_text"]
        val = update.message.text

        if val.upper() == "CALLBACK":
            cursor.execute(
                "INSERT INTO buttons VALUES (?, ?, NULL, ?)",
                (cid, text, "clicked"),
            )
        else:
            cursor.execute(
                "INSERT INTO buttons VALUES (?, ?, ?, NULL)",
                (cid, text, val),
            )
        db.commit()
        context.user_data.clear()
        await update.message.reply_text("✅ Button added")
        return


# ---------- BROADCAST ----------
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["broadcast"] = True
    await update.message.reply_text("Send broadcast message")


async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        update.effective_user.id != ADMIN_ID
        or not context.user_data.get("broadcast")
    ):
        return

    cursor.execute("SELECT user_id FROM users")
    for (uid,) in cursor.fetchall():
        try:
            await update.message.copy(uid)
            await asyncio.sleep(0.05)
        except:
            pass

    context.user_data["broadcast"] = False
    await update.message.reply_text("✅ Broadcast done")


# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT, admin_text))
    app.add_handler(MessageHandler(filters.ALL, handle_broadcast))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()

