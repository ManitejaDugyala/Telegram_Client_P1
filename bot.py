from dotenv import load_dotenv
load_dotenv()

import os
import sqlite3
import logging

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

# ========= LOGGING =========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ========= AUTO REPLY =========
PAID_AUTO_REPLY = """Welcome 👋 to nandu

Predictions & calculations only — no guarantees, no 100/100, no fixed reports.

This is not a money-printing machine. Results depend on your entry, exit, and discipline.

Only join if you can trade responsibly, stay in control, and accept risk.

If you’re looking for shortcuts or “sure shots”, this place isn’t for you.
"""

# ========= START MESSAGE =========
WELCOME_MSG = """Welcome to the channel.
Trade responsibly.

Wait for admin's reply.
"""

# ========= BOT =========
app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .concurrent_updates(True)
    .build()
)

# ========= DATABASE =========
conn = sqlite3.connect(
    "bot_database.db",
    check_same_thread=False,
    timeout=20
)

cur = conn.cursor()

# ========= TABLES =========

# Blocked users
cur.execute("""
CREATE TABLE IF NOT EXISTS blocked (
    user_id INTEGER PRIMARY KEY
)
""")

# Message mapping
cur.execute("""
CREATE TABLE IF NOT EXISTS message_map (
    forwarded_msg_id INTEGER PRIMARY KEY,
    user_id INTEGER
)
""")

conn.commit()

# ========= BLOCK FUNCTIONS =========
def is_blocked(user_id: int) -> bool:

    cur.execute(
        "SELECT 1 FROM blocked WHERE user_id=?",
        (user_id,)
    )

    return cur.fetchone() is not None


def block_user(user_id: int):

    cur.execute(
        "INSERT OR IGNORE INTO blocked VALUES (?)",
        (user_id,)
    )

    conn.commit()


def unblock_user(user_id: int):

    cur.execute(
        "DELETE FROM blocked WHERE user_id=?",
        (user_id,)
    )

    conn.commit()


# ========= START HANDLER =========
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.message:
        await update.message.reply_text(WELCOME_MSG)


# ========= USER HANDLER =========
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    user_id = update.message.from_user.id

    # ========= BLOCK CHECK =========
    # Silently ignore blocked users
    if is_blocked(user_id):
        return

    # ========= AUTO REPLY =========
    # Instant reply before membership check
    if update.message.text:

        text = update.message.text.lower()

        if "weekly paid" in text:

            try:
                await update.message.reply_text(
                    PAID_AUTO_REPLY
                )

            except Exception as e:
                logger.error(f"Auto reply failed: {e}")

    # ========= CHANNEL MEMBERSHIP CHECK =========
    # ONLY subscribers can use the bot

    try:

        member = await context.bot.get_chat_member(
            chat_id=CHANNEL_ID,
            user_id=user_id
        )

        # If user is NOT subscribed
        if member.status not in (
            "member",
            "administrator",
            "creator"
        ):

            # Silently ignore non-subscribers
            return

    except Exception as e:

        logger.error(f"Membership check failed: {e}")

        # IMPORTANT:
        # If Telegram fails to verify membership,
        # DO NOT process message
        return

    # ========= FORWARD MESSAGE TO ADMIN =========
    try:

        # NORMAL TELEGRAM FORWARD FORMAT
        forwarded_message = await update.message.forward(
            chat_id=ADMIN_ID
        )

        # SAVE MESSAGE MAPPING
        cur.execute(
            "INSERT OR REPLACE INTO message_map VALUES (?, ?)",
            (forwarded_message.message_id, user_id)
        )

        conn.commit()

    except Exception as e:

        logger.error(f"Forward message failed: {e}")


# ========= ADMIN HANDLER =========
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not update.message:
        return

    if update.message.from_user.id != ADMIN_ID:
        return

    # Admin must reply
    if not update.message.reply_to_message:
        return

    replied_msg_id = update.message.reply_to_message.message_id

    # ========= GET TARGET USER =========
    cur.execute(
        "SELECT user_id FROM message_map WHERE forwarded_msg_id=?",
        (replied_msg_id,)
    )

    result = cur.fetchone()

    if not result:

        await update.message.reply_text(
            "User mapping not found."
        )

        return

    target_user_id = result[0]

    # ========= TEXT =========
    if update.message.text:

        command = update.message.text.strip().lower()

        # ========= BLOCK =========
        if command == "/block":

            block_user(target_user_id)

            await update.message.reply_text(
                f"User {target_user_id} blocked successfully."
            )

            return

        # ========= UNBLOCK =========
        if command == "/unblock":

            unblock_user(target_user_id)

            await update.message.reply_text(
                f"User {target_user_id} unblocked successfully."
            )

            return

        # ========= NORMAL TEXT =========
        await context.bot.send_message(
            chat_id=target_user_id,
            text=update.message.text
        )

    # ========= PHOTO =========
    elif update.message.photo:

        photo = update.message.photo[-1]

        await context.bot.send_photo(
            chat_id=target_user_id,
            photo=photo.file_id,
            caption=update.message.caption or ""
        )

    # ========= VOICE =========
    elif update.message.voice:

        await context.bot.send_voice(
            chat_id=target_user_id,
            voice=update.message.voice.file_id
        )

    # ========= VIDEO =========
    elif update.message.video:

        await context.bot.send_video(
            chat_id=target_user_id,
            video=update.message.video.file_id,
            caption=update.message.caption or ""
        )

    # ========= DOCUMENT =========
    elif update.message.document:

        await context.bot.send_document(
            chat_id=target_user_id,
            document=update.message.document.file_id,
            caption=update.message.caption or ""
        )


# ========= ERROR HANDLER =========
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):

    logger.error(
        msg="Exception while handling update:",
        exc_info=context.error
    )


# ========= HANDLERS =========

# Start command
app.add_handler(
    CommandHandler("start", start_handler)
)

# User messages
app.add_handler(
    MessageHandler(
        filters.ALL & ~filters.User(ADMIN_ID),
        handle_user_message
    )
)

# Admin messages
app.add_handler(
    MessageHandler(
        filters.ALL & filters.User(ADMIN_ID),
        handle_admin_message
    )
)

# Error handler
app.add_error_handler(error_handler)

# ========= RUN =========
if __name__ == "__main__":

    print("Bot is running...")

    app.run_polling(
        poll_interval=0.5,
        timeout=30
    )
