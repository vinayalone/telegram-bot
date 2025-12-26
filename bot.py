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

# ---------- CONFIG ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5422522348

PROMO_PRICE = "₹499"
PAYMENT_UPI = "graphicinsight@axl"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# ---------- DATABASE ----------
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
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,),
    )
    db.commit()


def remove_user(user_id: int):
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    db.commit()


# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    save_user(update.effective_user.id)

    await update.message.reply_text(
        "Hello 👋\n"
        "This bot will approve & handle join requests automatically ✅\n\n"
        "For Ads Promotion - @EvilXStar\n\n"
        "💰 Paid Promotion: /promote"
    )


# ---------- JOIN REQUEST ----------
async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    save_user(user.id)

    image_url = "https://cricchamp.in/best-cricket-prediction-app/"
    caption = "🔥 *BEST PREDICTIONS CHANNELS* 🔥👇\n\n"

    keyboard = [
        [InlineKeyboardButton("🏏 CRICKET PREDICTION 🏏", url="https://t.me/+OnYD5obSG1JiY2I0")],
        [InlineKeyboardButton("❤️ AISHA QUEEN ❤️", url="https://t.me/+n2cVw6BE060zYWU1")],
        [InlineKeyboardButton("💥 IPL MATCH FIXER 💥", url="https://t.me/+zED2WoyVd5pjMWM1")],
        [InlineKeyboardButton("❤️ IPL KA BAAP ❤️", url="https://t.me/+11G8xkxyhK9jMTM9")],
        [InlineKeyboardButton("🎉 TODAY WINNER 🎉", url="https://t.me/+60uABbfEdZY1NjI9")],
        [InlineKeyboardButton("👑 DN SESSION KING 👑", url="https://t.me/+EEwGg6UIFFY0MGU1")],
        [InlineKeyboardButton("👸 FEMALE TIPPER 👸", url="https://t.me/+QfOSCO6H6uo3ODk1")],
    ]

    try:
        await context.bot.send_photo(
            chat_id=user.id,
            photo=image_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    except TelegramError:
        pass


# ---------- PAID PROMOTION ----------
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    await update.message.reply_text(
        "📢 *PAID PROMOTION DETAILS*\n\n"
        f"💼 Service: Channel Promotion\n"
        f"💰 Price: *{PROMO_PRICE}*\n\n"
        "💳 *Payment Method (UPI)*\n"
        f"• UPI ID: `{PAYMENT_UPI}`\n\n"
        "📌 *Instructions*\n"
        "1️⃣ Complete the payment\n"
        "2️⃣ Send your *ad message* here\n"
        "3️⃣ Admin will review & approve\n\n"
        "⏱ Approval Time: 1–24 hours",
        parse_mode="Markdown",
    )

    context.user_data["awaiting_promo"] = True


# ---------- RECEIVE PROMO ----------
async def receive_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    if not context.user_data.get("awaiting_promo"):
        return

    content = update.message.text
    user_id = update.effective_user.id

    cursor.execute(
        "INSERT INTO promotions (user_id, content) VALUES (?, ?)",
        (user_id, content),
    )
    db.commit()

    promo_id = cursor.lastrowid
    context.user_data["awaiting_promo"] = False

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{promo_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{promo_id}")]
    ])

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🆕 *New Paid Promotion Request*\n\n{content}",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

    await update.message.reply_text("✅ Promotion submitted. Await admin approval.")


# ---------- CALLBACK HANDLER ----------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not query.from_user:
        return

    await query.answer()

    if query.data == "count":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        await query.message.reply_text(f"👥 Total users: {total}")

    elif query.data == "broadcast":
        context.user_data["broadcast"] = True
        await query.message.reply_text("📢 Send the message you want to broadcast.")

    elif query.data.startswith("approve_"):
        promo_id = int(query.data.split("_")[1])
        cursor.execute("SELECT content FROM promotions WHERE id = ?", (promo_id,))
        row = cursor.fetchone()
        if not row:
            return

        content = row[0]
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        sent, removed = 0, 0
        for (user_id,) in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=content)
                sent += 1
                await asyncio.sleep(0.05)
            except TelegramError:
                remove_user(user_id)
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


# ---------- HANDLE BROADCAST ----------
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

    # 🚫 prevent conflict with paid promotion flow
    if context.user_data.get("awaiting_promo"):
        return

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("broadcast"):
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    sent, removed = 0, 0
    for (user_id,) in users:
        try:
            await update.message.copy(chat_id=user_id)
            sent += 1
            await asyncio.sleep(0.05)
        except TelegramError:
            remove_user(user_id)
            removed += 1

    context.user_data["broadcast"] = False
    await update.message.reply_text(
        f"✅ Broadcast sent: {sent}\n🚮 Removed: {removed}"
    )


# ---------- ERROR HANDLER ----------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Exception occurred:", exc_info=context.error)

# ---------- ADMIN PANEL ----------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return

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

# ---------- MAIN ----------
def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN missing in environment variables")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CallbackQueryHandler(callbacks))

    # 🔒 correct handler separation (CRITICAL)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_promo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast))

    app.add_error_handler(error_handler)

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()

