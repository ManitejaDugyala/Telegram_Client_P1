from dotenv import load_dotenv
load_dotenv()

import sqlite3
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# ========= CONFIG =========
BOT_TOKEN = "7676245660:AAGjvoKAYxHWrfm7lxjereGnfcLfoCBFdLw"
CHANNEL_ID = -1002083788429
ADMIN_ID = 8595659152
# ==========================

# Auto reply message for "paid"
PAID_AUTO_REPLY = """"Welcome 👋 to nandu
Predictions & calculations only — no guarantees, no 100/100, no fixed reports.
This is not a money-printing machine. Results depend on your entry, exit, and discipline.
Only join if you can trade responsibly, stay in control, and accept risk.
If you’re looking for shortcuts or “sure shots”, this place isn’t for you."""

app = ApplicationBuilder().token(BOT_TOKEN).build()

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
# admin_message_id -> user_id
user_map = {}

# ---------- USER HANDLER (TEXT + PHOTO) ----------
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user_id = update.message.from_user.id

    # Ignore blocked users
    if is_blocked(user_id):
        return

    # Channel subscription check
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status not in ("member", "administrator", "creator"):
            return
    except:
        return

    # 🔥 AUTO REPLY FOR "paid" (case-insensitive)
    if update.message.text:
        if update.message.text.strip().lower() == "paid":
            await update.message.reply_text(PAID_AUTO_REPLY)
            # DO NOT return → message must still reach admin

    # 🔥 REAL FORWARD (shows "Forwarded from @username")
    forwarded = await update.message.forward(chat_id=ADMIN_ID)

    # Map admin message → original user
    user_map[forwarded.message_id] = user_id


# ---------- ADMIN HANDLER (TEXT + PHOTO REPLY) ----------
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.message.from_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        return

    replied_msg_id = update.message.reply_to_message.message_id
    if replied_msg_id not in user_map:
        return

    target_user_id = user_map[replied_msg_id]

    # TEXT REPLY
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

    # PHOTO REPLY
    elif update.message.photo:
        photo = update.message.photo[-1]
        caption = update.message.caption or ""

        await context.bot.send_photo(
            chat_id=target_user_id,
            photo=photo.file_id,
            caption=caption
        )

# ---------- HANDLERS ----------
app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO) & ~filters.User(ADMIN_ID),
        handle_user_message
    )
)

app.add_handler(
    MessageHandler(
        (filters.TEXT | filters.PHOTO) & filters.User(ADMIN_ID),
        handle_admin_message
    )
)

# ---------- RUN ----------
if __name__ == "__main__":
    print("Bot is running...")
    app.run_polling()
