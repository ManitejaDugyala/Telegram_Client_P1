from dotenv import load_dotenv
load_dotenv()

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import sqlite3
import os

# ========= CONFIG =========
BOT_TOKEN = "7676245660:AAGjvoKAYxHWrfm7lxjereGnfcLfoCBFdLw"
CHANNEL_ID = -1002083788429
ADMIN_ID = 8595659152
# ==========================

# ---------- AUTO REPLY ----------
PAID_AUTO_REPLY = """Welcome 👋 to nandu
Predictions & calculations only — no guarantees, no 100/100, no fixed reports.
This is not a money-printing machine. Results depend on your entry, exit, and discipline.
Only join if you can trade responsibly, stay in control, and accept risk.
If you’re looking for shortcuts or “sure shots”, this place isn’t for you."""

# ---------- BANNED WORDS ----------
BANNED_WORDS = {
    "dengey","sulliga","savadengutha","puku","puka","sulli",
    "ammani","lanjakoduka","lnjkdka","thu ni bathuku",
    "mingey","dengutha","akkani","madharchot",
    "markelowde","lowde","bulle","sakkaga puttinodu"
}

# ---------- DATABASE ----------
conn = sqlite3.connect("blocked_users.db", check_same_thread=False)
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS blocked (user_id INTEGER PRIMARY KEY)")
conn.commit()

def is_blocked(uid):
    cur.execute("SELECT 1 FROM blocked WHERE user_id=?", (uid,))
    return cur.fetchone() is not None

def block_user(uid):
    cur.execute("INSERT OR IGNORE INTO blocked VALUES (?)", (uid,))
    conn.commit()

def unblock_user(uid):
    cur.execute("DELETE FROM blocked WHERE user_id=?", (uid,))
    conn.commit()

# ---------- USER MAP ----------
user_map = {}  # admin_msg_id -> user_id

# ---------- USER → ADMIN ----------
async def handle_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    user_id = user.id
    text = (update.message.text or "").lower()

    if is_blocked(user_id):
        return

    # Subscription check
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status not in ("member", "administrator", "creator"):
            return
    except:
        return

    # Foul word detection → auto block
    for word in BANNED_WORDS:
        if word in text:
            block_user(user_id)
            return

    # Auto reply for "paid"
    if text.strip() == "paid":
        await update.message.reply_text(PAID_AUTO_REPLY)

    # ---- TEXT ----
    if update.message.text:
        forwarded = await update.message.forward(chat_id=ADMIN_ID)
        user_map[forwarded.message_id] = user_id

    # ---- PHOTO ----
    if update.message.photo:
        forwarded = await update.message.forward(chat_id=ADMIN_ID)
        user_map[forwarded.message_id] = user_id

# ---------- ADMIN → USER ----------
async def handle_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or update.effective_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        return

    replied_id = update.message.reply_to_message.message_id
    if replied_id not in user_map:
        return

    target_user = user_map[replied_id]
    command = (update.message.text or "").lower().strip()

    # Commands
    if command == "/block":
        block_user(target_user)
        return

    if command == "/unblock":
        unblock_user(target_user)
        return

    # ---- TEXT ----
    if update.message.text:
        await context.bot.send_message(target_user, update.message.text)

    # ---- PHOTO ----
    if update.message.photo:
        photo = update.message.photo[-1]
        caption = update.message.caption or ""
        await context.bot.send_photo(
            target_user,
            photo.file_id,
            caption
        )

# ---------- MAIN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(MessageHandler(~filters.User(ADMIN_ID), handle_user))
app.add_handler(MessageHandler(filters.User(ADMIN_ID), handle_admin))

print("Bot running...")
app.run_polling()
