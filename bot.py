from dotenv import load_dotenv
load_dotenv()

import os
import telebot

import sqlite3
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)
# IMAGE SUPPORT TEST

# ========= CONFIG =========
# BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_TOKEN = "7676245660:AAGjvoKAYxHWrfm7lxjereGnfcLfoCBFdLw"
bot = telebot.TeleBot(BOT_TOKEN)
CHANNEL_ID = -1002083788429
ADMIN_ID = 8595659152
# ==========================

# Auto reply message for "paid"
PAID_AUTO_REPLY = """Welcome 👋 to nandu
Predictions & calculations only — no guarantees, no 100/100, no fixed reports.
This is not a money-printing machine. Results depend on your entry, exit, and discipline.
Only join if you can trade responsibly, stay in control, and accept risk.
If you’re looking for shortcuts or “sure shots”, this place isn’t for you."""
user_message_map = {}  # forwarded_message_id -> user_id

# Add abusive words here (lowercase)
BANNED_WORDS = {
    "dengey",
    "sulliga",
    "savadengutha",
    "puku",
    "puka",
    "sulli",
    "ammani",
    "lanjakoduka",
    "lnjkdka",
    "thu ni bathuku",
    "mingey",
    "dengutha",
    "akkani ",
    "madharchot",
    "markelowde",
    "lowde",
    "bulle",
    "sakkaga puttinodu"
}
@bot.message_handler(content_types=['text'])
def user_text(message):
    if message.chat.id == ADMIN_ID:
        return

    forwarded = bot.send_message(
        ADMIN_ID,
        f"👤 User ID: {message.chat.id}\n\n{message.text}"
    )

    user_message_map[forwarded.message_id] = message.chat.id


@bot.message_handler(content_types=['photo'])
def user_photo(message):
    if message.chat.id == ADMIN_ID:
        return

    file_id = message.photo[-1].file_id
    caption = message.caption if message.caption else ""

    forwarded = bot.send_photo(
        ADMIN_ID,
        file_id,
        caption=f"👤 User ID: {message.chat.id}\n\n{caption}"
    )

    user_message_map[forwarded.message_id] = message.chat.id


@bot.message_handler(
    content_types=['text'],
    func=lambda msg: msg.chat.id == ADMIN_ID and msg.reply_to_message is not None
)
def admin_reply_text(message):
    replied_id = message.reply_to_message.message_id

    if replied_id in user_message_map:
        user_id = user_message_map[replied_id]
        bot.send_message(user_id, message.text)

@bot.message_handler(
    content_types=['photo'],
    func=lambda msg: msg.chat.id == ADMIN_ID and msg.reply_to_message is not None
)
def admin_reply_photo(message):
    replied_id = message.reply_to_message.message_id

    if replied_id in user_message_map:
        user_id = user_message_map[replied_id]
        file_id = message.photo[-1].file_id
        caption = message.caption if message.caption else ""

        bot.send_photo(user_id, file_id, caption)



# ---------- DATABASE ----------
conn = sqlite3.connect("blocked_users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS blocked (user_id INTEGER PRIMARY KEY)")
conn.commit()

def is_blocked(user_id: int) -> bool:
    cur.execute("SELECT 1 FROM blocked WHERE user_id=?", (user_id,))
    return cur.fetchone() is not None

def block_user(user_id: int):
    cur.execute("INSERT OR IGNORE INTO blocked VALUES (?)", (user_id,))
    conn.commit()

def unblock_user(user_id: int):
    cur.execute("DELETE FROM blocked WHERE user_id=?", (user_id,))
    conn.commit()

# ---------- USER MAP ----------
user_map = {}  # admin_message_id -> user_id

# ---------- USER MESSAGE HANDLER ----------
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.message.from_user
    user_id = user.id
    text = (update.message.text or "").lower()

    # Blocked users ignored silently
    if is_blocked(user_id):
        return

    # Check channel subscription
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status not in ("member", "administrator", "creator"):
            return
    except:
        return

    # Abusive word check (AUTO BLOCK)
    for word in BANNED_WORDS:
        if word in text:
            block_user(user_id)
            return

    # Auto reply for "paid" (case-insensitive)
    if text.strip() == "paid":
        await update.message.reply_text(PAID_AUTO_REPLY)
        # NOTE: no return here → message will still go to admin

    # Forward message to admin
    forwarded = await update.message.forward(chat_id=ADMIN_ID)
    user_map[forwarded.message_id] = user_id

# ---------- ADMIN HANDLER ----------
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.from_user.id != ADMIN_ID:
        return

    msg = update.message

    if not msg.reply_to_message:
        return

    replied_msg_id = msg.reply_to_message.message_id
    if replied_msg_id not in user_map:
        return

    target_user_id = user_map[replied_msg_id]
    command = (msg.text or "").strip().lower()

    if command == "/block":
        block_user(target_user_id)
        return

    if command == "/unblock":
        unblock_user(target_user_id)
        return

    # Normal reply to user
    await context.bot.send_message(
        chat_id=target_user_id,
        text=msg.text
    )

# ---------- MAIN ----------
if __name__ == "__main__":
    print("Bot is starting...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Exclude admin from user handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID),
            handle_user_message
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.User(ADMIN_ID),
            handle_admin_message
        )
    )

    print("Bot is running...")
    app.run_polling()
