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

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5422522348

PROMO_PRICE = "₹499"
PAYMENT_UPI = "graphicinsight@axl"

PROMO_IMAGE = "https://i.imgur.com/5KXJ7Qp.jpg"  # ✅ direct image URL

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------------- DATABASE ----------------
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content TEXT
)
""")
db.commit()


def save_user(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    db.commit()


def remove_user(user_id: int):
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    db.commit()


# ---------------- /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_user.id
    save_user(user_id)

    await update.message.reply_text(
        "👋 Hello!\n\n"
        "This bot sends promotional messages automatically.\n\n"
        "💰 Paid Promotion: /promote"
    )


# ---------------- JOIN REQUEST (NO APPROVAL) ----------------
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    save_user(user.id)

    caption = (
        "🔥 *BEST PREDICTION CHANNELS* 🔥\n\n"
        "Join trusted & winning channels below 👇"
    )

    keyboard = [
        [InlineKeyboardButton("🏏 CRICKET PREDICTION 🏏", url="https://t.me/+OnYD5obSG1JiY2I0")],
        [InlineKeyboardButton("❤️ AISHA QUEEN ❤️", url="https://t.me/+n2cVw6BE060zYWU1")],
        [InlineKeyboardButton("💥 IPL MATCH FIXER 💥", url="https://t.me/+zED2WoyVd5pjMWM1")],
        [InlineKeyboardButton("🎉 TODAY WINNER 🎉", url="https://t.me/+60uABbfEdZY1NjI9")],
    ]

    try:
        await context.bot.send_photo(
            chat_id=user.id,
            photo=PROMO_IMAGE,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    except TelegramError:
        pass

    # ❌ DO NOT approve join request
    # User stays unapproved intentionally


# ---------------- PAID PROMOTION ----------------
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    context.user_data.clear()
    context.user_data["awaiting_promo"] = True

    await update.message.reply_text(
        "📢 *PAID PROMOTION DETAILS*\n\n"
        f"💼 Service: Channel Promotion\n"
        f"💰 Price: *{PROMO_PRICE}*\n\n"
        "💳 *Payment (UPI)*\n"
        f"`{PAYMENT_UPI}`\n\n"
        "📌 After payment, send your ad message here.",
        parse_mode="Markdown",
    )


# ---------------- RECEIVE PROMO MESSAGE ----------------
async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.effective_user.id
    text = update.message.text

    # ----- PROMO FLOW -----
    if context.user_data.get("awaiting_promo"):
        cursor.execute(
            "INSERT INTO promotions (user_id, content) VALUES (?, ?)",
            (user_id, text),
        )
        db.commit()

        promo_id = cursor.lastrowid
        context.user_data.clear()

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{promo_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{promo_id}")
            ]
        ])

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 *New Promotion Request*\n\n{text}",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        await update.message.reply_text("✅ Promotion sent for admin approval.")
        return

    # ----- BROADCAST FLOW -----
    if (
        user_id == ADMIN_ID
        and context.application.bot_data.get("broadcast")
    ):
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = removed = 0
        for (uid,) in users:
            try:
                await update.message.copy(chat_id=uid)
                sent += 1
                await asyncio.sleep(0.1)
            except TelegramError:
                remove_user(uid)
                removed += 1

        context.application.bot_data["broadcast"] = False
        await update.message.reply_text(
            f"✅ Broadcast completed\n📤 Sent: {sent}\n🚮 Removed: {removed}"
        )


# ---------------- CALLBACK HANDLER ----------------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Unauthorized", show_alert=True)
        return

    if query.data == "count":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        await query.message.reply_text(f"👥 Total users: {total}")

    elif query.data == "broadcast":
        context.application.bot_data["broadcast"] = True
        await query.message.reply_text("📢 Send broadcast message now.")

    elif query.data.startswith("approve_"):
        promo_id = int(query.data.split("_")[1])
        cursor.execute("SELECT content FROM promotions WHERE id = ?", (promo_id,))
        row = cursor.fetchone()
        if not row:
            return

        content = row[0]
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent = removed = 0
        for (uid,) in users:
            try:
                await context.bot.send_message(chat_id=uid, text=content)
                sent += 1
                await asyncio.sleep(0.1)
            except TelegramError:
                remove_user(uid)
                removed += 1

        cursor.execute("DELETE FROM promotions WHERE id = ?", (promo_id,))
        db.commit()

        await query.message.edit_text(
            f"✅ Promotion Approved\n📤 Sent: {sent}\n🚮 Removed: {removed}"
        )

    elif query.data.startswith("reject_"):
        promo_id = int(query.data.split("_")[1])
        cursor.execute("DELETE FROM promotions WHERE id = ?", (promo_id,))
        db.commit()
        await query.message.edit_text("❌ Promotion Rejected")


# ---------------- ADMIN PANEL ----------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
        [InlineKeyboardButton("📊 Total Users", callback_data="count")],
    ]

    await update.message.reply_text(
        "🛠 *Admin Panel*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ---------------- ERROR HANDLER ----------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Error:", exc_info=context.error)


# ---------------- MAIN ----------------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("promote", promote))

    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text))

    app.add_error_handler(error_handler)

    print("🤖 Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
