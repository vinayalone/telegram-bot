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

# ---------- CONFIG ----------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 5422522348

PROMO_PRICE = "₹499"
PAYMENT_UPI = "graphicinsight@axl"

logging.basicConfig(level=logging.INFO)

# ---------- DATABASE ----------
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    payment_file TEXT,
    promo_type TEXT,
    promo_file TEXT,
    promo_text TEXT
)
""")
db.commit()


def save_user(user_id: int):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
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
        "For Support - @EvilXStar\n\n"
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
    context.user_data.clear()
    context.user_data["promo_step"] = "payment"

    await update.message.reply_text(
        f"📢 *PAID PROMOTION*\n\n"
        f"💰 Price: *{PROMO_PRICE}*\n"
        f"💳 UPI ID: `{PAYMENT_UPI}`\n\n"
        "📸 *Please send payment screenshot now*",
        parse_mode="Markdown",
    )


# ---------- RECEIVE PAYMENT ----------
async def receive_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("promo_step") != "payment":
        return

    if not update.message.photo:
        await update.message.reply_text("❌ Please send payment screenshot.")
        return

    context.user_data["payment_file"] = update.message.photo[-1].file_id
    context.user_data["promo_step"] = "content"

    await update.message.reply_text(
        "✅ Payment received.\n\n"
        "📤 Now send promotion:\n"
        "• Text OR\n"
        "• Image with caption"
    )


# ---------- RECEIVE PROMO CONTENT ----------
async def receive_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("promo_step") != "content":
        return

    promo_type = "text"
    promo_file = None
    promo_text = update.message.text or ""

    if update.message.photo:
        promo_type = "photo"
        promo_file = update.message.photo[-1].file_id
        promo_text = update.message.caption or ""

    cursor.execute(
        """
        INSERT INTO promotions
        (user_id, payment_file, promo_type, promo_file, promo_text)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            update.effective_user.id,
            context.user_data["payment_file"],
            promo_type,
            promo_file,
            promo_text,
        ),
    )
    db.commit()

    promo_id = cursor.lastrowid
    context.user_data.clear()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{promo_id}")],
        [InlineKeyboardButton("❌ Reject", callback_data=f"reject_{promo_id}")]
    ])

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=context.user_data.get("payment_file"),
        caption="🧾 Payment Proof"
    )

    if promo_type == "photo":
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=promo_file,
            caption=promo_text,
            reply_markup=keyboard,
        )
    else:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=promo_text,
            reply_markup=keyboard,
        )

    await update.message.reply_text("✅ Sent for admin approval.")


# ---------- CALLBACK HANDLER ----------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("approve_"):
        promo_id = int(query.data.split("_")[1])

        cursor.execute(
            "SELECT promo_type, promo_file, promo_text FROM promotions WHERE id=?",
            (promo_id,),
        )
        promo_type, promo_file, promo_text = cursor.fetchone()

        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

        for (user_id,) in users:
            try:
                if promo_type == "photo":
                    await context.bot.send_photo(
                        chat_id=user_id,
                        photo=promo_file,
                        caption=promo_text,
                    )
                else:
                    await context.bot.send_message(chat_id=user_id, text=promo_text)

                await asyncio.sleep(0.05)
            except TelegramError:
                remove_user(user_id)

        cursor.execute("DELETE FROM promotions WHERE id=?", (promo_id,))
        db.commit()

        await query.message.edit_text("✅ Promotion approved & sent.")

    elif query.data.startswith("reject_"):
        promo_id = int(query.data.split("_")[1])
        cursor.execute("DELETE FROM promotions WHERE id=?", (promo_id,))
        db.commit()
        await query.message.edit_text("❌ Promotion rejected.")


# ---------- HANDLE BROADCAST ----------
async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("promo_step"):
        return

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.user_data.get("broadcast"):
        return

    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()

    for (user_id,) in users:
        try:
            await update.message.copy(chat_id=user_id)
            await asyncio.sleep(0.05)
        except TelegramError:
            remove_user(user_id)

    context.user_data["broadcast"] = False
    await update.message.reply_text("✅ Broadcast completed.")


# ---------- ERROR HANDLER ----------
async def error_handler(update, context):
    logging.error("Error:", exc_info=context.error)


# ---------- ADMIN PANEL ----------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="broadcast")],
    ]

    await update.message.reply_text(
        "🛠 Admin Panel",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CallbackQueryHandler(callbacks))

    app.add_handler(MessageHandler(filters.PHOTO, receive_payment))
    app.add_handler(MessageHandler(filters.ALL, receive_promo))
    app.add_handler(MessageHandler(filters.ALL, handle_broadcast))

    app.add_error_handler(error_handler)

    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
