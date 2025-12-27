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

PROMO_PLANS = {
    "1000": ("₹499", 1000),
    "5000": ("₹1999", 5000),
    "10000": ("₹3499", 10000),
}

PAYMENT_UPI = "graphicinsight@axl"
PROMO_IMAGE = "https://i.imgur.com/5KXJ7Qp.jpg"

logging.basicConfig(level=logging.INFO)

# ---------------- DATABASE ----------------
db = sqlite3.connect("users.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
cursor.execute("""
CREATE TABLE IF NOT EXISTS promotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    content TEXT,
    photo_id TEXT,
    limit_users INTEGER
)
""")
db.commit()


def save_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (user_id,))
    db.commit()


def remove_user(user_id):
    cursor.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    db.commit()


# ---------------- /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user(update.effective_user.id)

    await update.message.reply_text(
        "👋 Hello!\n\n"
        "This bot sends promotional messages automatically.\n\n"
        "We have 100k+ Users of data & of all Category\n\n"
        "For Paid Promotion: /promote\n"
        "Support: @EvilxStar"
    )


# ---------------- /promote ----------------
async def promote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1000 Users – ₹499", callback_data="plan_1000")],
        [InlineKeyboardButton("5000 Users – ₹1999", callback_data="plan_5000")],
        [InlineKeyboardButton("10000 Users – ₹3499", callback_data="plan_10000")],
    ]

    await update.message.reply_text(
        "📢 *PAID PROMOTION DETAILS*\n\n"
        "💼 Service: Channel Promotion\n\n"
        "💳 Payment Method (UPI)\n"
        f"• `{PAYMENT_UPI}`\n\n"
        "📌 Instructions\n"
        "1️⃣ Choose a plan\n"
        "2️⃣ Complete the payment\n"
        "3️⃣ Send payment screenshot\n\n"
        "⏱️ Approval Time: 1–24 hours",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ---------------- JOIN REQUEST (ONLY DM PROMO) ----------------
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


# ---------------- CALLBACKS ----------------
async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("❌ Unauthorized", show_alert=True)
        return

    # ----- ADMIN COUNT -----
    if query.data == "admin_count":
        cursor.execute("SELECT COUNT(*) FROM users")
        total = cursor.fetchone()[0]
        await query.message.reply_text(f"📊 Total Users: {total}")
        return

    # ----- ADMIN BROADCAST -----
    if query.data == "admin_broadcast":
        context.application.bot_data["broadcast"] = True
        await query.message.reply_text("📢 Send the broadcast message now.")
        return


    if query.data.startswith("plan_"):
        plan_key = query.data.split("_")[1]
        price, limit_users = PROMO_PLANS[plan_key]

        context.user_data["plan"] = limit_users
        context.user_data["awaiting_payment"] = True

        await query.message.reply_text(
            f"✅ *Plan Selected*\n\n"
            f"Users: {limit_users}\n"
            f"Price: {price}\n\n"
            "📸 Now send your *payment screenshot*.",
            parse_mode="Markdown",
        )
        return

    if query.from_user.id != ADMIN_ID:
        return

    if query.data.startswith("approve_"):
        promo_id = int(query.data.split("_")[1])
        cursor.execute("SELECT content, limit_users FROM promotions WHERE id=?", (promo_id,))
        content, limit_users = cursor.fetchone()

        cursor.execute("SELECT user_id FROM users LIMIT ?", (limit_users,))
        users = cursor.fetchall()

        sent = 0
        for (uid,) in users:
            try:
                await context.bot.send_message(uid, content)
                sent += 1
                await asyncio.sleep(0.1)
            except TelegramError:
                remove_user(uid)

        cursor.execute("DELETE FROM promotions WHERE id=?", (promo_id,))
        db.commit()

        await query.message.edit_text(f"✅ Approved & Sent to {sent} users")

    if query.data.startswith("reject_"):
        promo_id = int(query.data.split("_")[1])
        cursor.execute("DELETE FROM promotions WHERE id=?", (promo_id,))
        db.commit()
        await query.message.edit_text("❌ Promotion Rejected")


# ---------------- RECEIVE USER DATA ----------------
async def receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
async def receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # ---------- ADMIN BROADCAST ----------
    if (
        update.effective_user.id == ADMIN_ID
        and context.application.bot_data.get("broadcast")
        and update.message
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
            f"✅ Broadcast Done\n📤 Sent: {sent}\n🚮 Removed: {removed}"
        )
        return

    # ---------- PAYMENT SCREENSHOT ----------
    if context.user_data.get("awaiting_payment") and update.message.photo:
        ...

    # PAYMENT SCREENSHOT
    if context.user_data.get("awaiting_payment") and update.message.photo:
        context.user_data["payment_photo"] = update.message.photo[-1].file_id
        context.user_data["awaiting_payment"] = False
        context.user_data["awaiting_ad"] = True

        await context.bot.send_photo(
            ADMIN_ID,
            photo=context.user_data["payment_photo"],
            caption=f"💰 Payment Screenshot\nUser: {user_id}",
        )

        await update.message.reply_text(
            "✅ Payment screenshot received.\n\n"
            "📩 Now send your *ad message*."
        )
        return

    # AD MESSAGE
    if context.user_data.get("awaiting_ad") and update.message.text:
        cursor.execute(
            "INSERT INTO promotions (user_id, content, limit_users) VALUES (?, ?, ?)",
            (
                user_id,
                update.message.text,
                context.user_data["plan"],
            ),
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
            ADMIN_ID,
            f"🆕 *New Promotion*\n\nUsers: {PROMO_PLANS[str(context.user_data.get('plan', 1000))][0]}\n\n{update.message.text}",
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        await update.message.reply_text("⏳ Your promotion is under review.")
        return
# ---------------- ADMIN PANEL ----------------
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Total Users", callback_data="admin_count")],
    ]

    await update.message.reply_text(
        "🛠 *Admin Panel*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("promote", promote))
    app.add_handler(ChatJoinRequestHandler(join_request))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.ALL, receive))

    print("🤖 Bot Running...")
    app.run_polling()


if __name__ == "__main__":
    main()


