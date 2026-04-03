from dotenv import load_dotenv
load_dotenv()

import sqlite3
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
    CommandHandler
)

# ========= CONFIG =========
BOT_TOKEN = "7676245660:AAGjvoKAYxHWrfm7lxjereGnfcLfoCBFdLw"
CHANNEL_ID = -1002083788429
ADMIN_ID = 8595659152
# ==========================	

# Auto reply message for "weekly paid"
PAID_AUTO_REPLY = """Welcome 👋 to nandu
Predictions & calculations only — no guarantees, no 100/100, no fixed reports.
This is not a money-printing machine. Results depend on your entry, exit, and discipline.
Only join if you can trade responsibly, stay in control, and accept risk.
If you’re looking for shortcuts or “sure shots”, this place isn’t for you."""

# Start message
WELCOME_MSG = """Welcome to the channel,Trade responsible.
Wait for admin's reply."""

app = ApplicationBuilder().token(BOT_TOKEN).build()

# ---------- DATABASE ----------
conn = sqlite3.connect("blocked_users.db", check_same_thread=False, timeout=10)
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
user_map = {}

# ---------- START HANDLER ----------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(WELCOME_MSG)

# ---------- USER HANDLER ----------
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.message.from_user.id

    if is_blocked(user_id):
        return

    # Channel subscription check
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status not in ("member", "administrator", "creator"):
            return
    except Exception as e:
        print("Membership check failed:", e)
        return

    # 🔥 AUTO REPLY FOR "weekly paid"
    if update.message.text:
        text = update.message.text.lower()
        if "weekly paid" in text:
            await asyncio.sleep(0.3)  # avoid rate limit
            await update.message.reply_text(PAID_AUTO_REPLY)

    # 🔥 FORWARD ALL TYPES
    forwarded = await update.message.forward(chat_id=ADMIN_ID)
    user_map[forwarded.message_id] = user_id


# ---------- ADMIN HANDLER ----------
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.from_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        return

    replied_msg_id = update.message.reply_to_message.message_id
    if replied_msg_id not in user_map:
        return

    target_user_id = user_map[replied_msg_id]

    # TEXT
    if update.message.text:
        command = update.message.text.strip().lower()

        if command == "/block":
            block_user(target_user_id)
            return

        if command == "/unblock":
            unblock_user(target_user_id)
            return

        await context.bot.send_message(
            chat_id=target_user_id,
            text=update.message.text
        )

    # PHOTO
    elif update.message.photo:
        photo = update.message.photo[-1]
        caption = update.message.caption or ""

        await context.bot.send_photo(
            chat_id=target_user_id,
            photo=photo.file_id,
            caption=caption
        )

    # 🎤 VOICE
    elif update.message.voice:
        await context.bot.send_voice(
            chat_id=target_user_id,
            voice=update.message.voice.file_id
        )


# ---------- HANDLERS ----------
app.add_handler(CommandHandler("start", start_handler))

app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VOICE) & ~filters.User(ADMIN_ID),
        handle_user_message
    )
)

app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO | filters.VOICE) & filters.User(ADMIN_ID),
        handle_admin_message
    )
)

# ---------- RUN ----------
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)