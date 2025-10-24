# bot.py
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import psutil
import time
import os
import subprocess
import asyncio
from config import BOT_TOKEN, OWNER_ID
from database import Database
from stream_manager import StreamManager

# Initialize database and stream manager
db = Database()
stream_manager = StreamManager()
start_time = time.time()

# Rate limiting: user_id -> last command time
last_command = {}

# Utility to check if user is authorized
async def is_authorized_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    return user_id == OWNER_ID or db.is_authorized(user_id)

# Rate limit decorator
def rate_limit(seconds=2):
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            now = time.time()
            if user_id in last_command and now - last_command[user_id] < seconds:
                if update.message:
                    await update.message.reply_text("Please wait a moment before using another command.")
                return
            last_command[user_id] = now
            return await func(update, context)
        return wrapper
    return decorator

# Auto-delete message
async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.message:
            await update.message.delete()
    except:
        pass  # Ignore if can't delete

# /start command
@rate_limit(2)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this bot.")
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Welcome to the Stream Bot! Use /help to see available commands."
    )

# /stream command
@rate_limit(3)
async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not authorized to use this command."
        )
        return

    args = context.args
    if len(args) < 4:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /stream <m3u8_link> <rtmp_url> <stream_key> <stream_title>"
        )
        return

    m3u8_link = args[0]
    rtmp_url = args[1]
    stream_key = args[2]
    stream_title = " ".join(args[3:])

    if not all([m3u8_link, rtmp_url, stream_key, stream_title]):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="All fields are required and cannot be empty."
        )
        return

    try:
        user_id = update.effective_user.id
        stream_id = stream_manager.start_stream(m3u8_link, rtmp_url, stream_key, stream_title)
        db.add_stream(stream_id, m3u8_link, rtmp_url, stream_key, stream_title, user_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream started!\nID: `{stream_id}`\nTitle: {stream_title}",
            parse_mode='Markdown'
        )
        print(f"[STREAM STARTED] ID: {stream_id} | User: {user_id}")
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to start stream:\n`{str(e)}`",
            parse_mode='Markdown'
        )
        print(f"[STREAM FAILED] User: {user_id} | Error: {e}")

# /streaminfo command
@rate_limit(3)
async def streaminfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    user_id = update.effective_user.id
    if not await is_authorized_user(update, context):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not authorized to use this command."
        )
        return

    streams = db.get_all_streams() if user_id == OWNER_ID else db.get_user_streams(user_id)

    if not streams:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No active streams."
        )
        return

    for stream in streams:
        stream_id, m3u8_link, _, _, stream_title, _, _ = stream
        duration = stream_manager.get_stream_duration(stream_id)
        thumbnail_path = f"/tmp/{stream_id}_thumb.jpg"
        message = f"*Stream ID:* `{stream_id}`\n*Title:* {telegram.utils.helpers.escape_markdown(stream_title, version=2)}\n*Duration:* {duration or 'Starting...'}"
        
        keyboard = [[InlineKeyboardButton("Stop Stream", callback_data=f"stop_{stream_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
            if os.path.exists(thumbnail_path):
                with open(thumbnail_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo,
                        caption=message,
                        parse_mode='MarkdownV2',
                        reply_markup=reply_markup
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{message}\n\nWarning: Thumbnail not ready yet.",
                    parse_mode='MarkdownV2',
                    reply_markup=reply_markup
                )
        except Exception as e:
            print(f"[THUMBNAIL ERROR] Stream {stream_id}: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message + "\n\nWarning: Could not send thumbnail.",
                parse_mode='MarkdownV2',
                reply_markup=reply_markup
            )

# /stop command
@rate_limit(2)
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    user_id = update.effective_user.id
    if not await is_authorized_user(update, context):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not authorized to use this command."
        )
        return

    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /stop <stream_id>"
        )
        return

    stream_id = context.args[0]
    stream = db.get_stream(stream_id)
    if not stream:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream `{stream_id}` not found."
        )
        return
    if user_id != OWNER_ID and stream[5] != user_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You can only stop your own streams."
        )
        return

    if stream_manager.stop_stream(stream_id):
        db.remove_stream(stream_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream `{stream_id}` stopped successfully."
        )
        print(f"[STREAM STOPPED] ID: {stream_id} | User: {user_id}")
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream `{stream_id}` not running."
        )

# Inline button handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if not await is_authorized_user(update, context):
        await query.edit_message_caption(caption="Unauthorized action.")
        return

    if not query.data.startswith("stop_"):
        return

    stream_id = query.data.replace("stop_", "")
    stream = db.get_stream(stream_id)
    if not stream:
        await query.edit_message_caption(caption=f"Stream `{stream_id}` not found.")
        return
    if user_id != OWNER_ID and stream[5] != user_id:
        await query.edit_message_caption(caption="You can only stop your own streams.")
        return

    if stream_manager.stop_stream(stream_id):
        db.remove_stream(stream_id)
        await query.edit_message_caption(caption=f"Stream `{stream_id}` stopped.")
        print(f"[STREAM STOPPED VIA BUTTON] ID: {stream_id} | User: {user_id}")
    else:
        await query.edit_message_caption(caption=f"Stream `{stream_id}` already stopped.")

# /ping command (owner only)
@rate_limit(3)
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Owner-only command."
        )
        return

    uptime = time.time() - start_time
    uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
    cpu = psutil.cpu_percent()
    disk = psutil.disk_usage('/')
    mem = psutil.virtual_memory()

    response = (
        f"*Bot Stats*\n\n"
        f"Uptime: `{uptime_str}`\n"
        f"CPU: `{cpu}%`\n"
        f"Storage: `{disk.used // (1024**3)} GB / {disk.total // (1024**3)} GB`\n"
        f"RAM: `{mem.used // (1024**3)} GB / {mem.total // (1024**3)} GB`"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response,
        parse_mode='Markdown'
    )

# /reboot command (owner only)
@rate_limit(5)
async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Owner-only command."
        )
        return

    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Stopping all streams and rebooting VPS..."
    )

    try:
        streams = db.get_all_streams()
        for stream in streams:
            stream_id = stream[0]
            stream_manager.stop_stream(stream_id)
            db.remove_stream(stream_id)
        print(f"[REBOOT] All {len(streams)} streams stopped.")

        await msg.edit_text("Rebooting now...")
        print("[REBOOT] Initiating system reboot...")
        subprocess.run(["sudo", "reboot"], check=False)
    except Exception as e:
        await msg.edit_text(f"Reboot failed: `{str(e)}`")
        print(f"[REBOOT FAILED] {e}")

# /auth and /deauth
@rate_limit(2)
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Owner only.")
        return
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /auth <telegram_id>")
        return
    try:
        uid = int(context.args[0])
        db.add_user(uid)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"User `{uid}` authorized.")
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid ID.")

@rate_limit(2)
async def deauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Owner only.")
        return
    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /deauth <telegram_id>")
        return
    try:
        uid = int(context.args[0])
        db.remove_user(uid)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"User `{uid}` deauthorized.")
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid ID.")

# /help command
@rate_limit(2)
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Unauthorized."
        )
        return

    help_text = (
        "*Stream Bot Commands*\n\n"
        "/start - Welcome message\n"
        "/stream `<m3u8> <rtmp> <key> <title>` - Start stream\n"
        "/streaminfo - List active streams\n"
        "/stop `<id>` - Stop a stream\n"
        "/help - This message\n"
    )
    if update.effective_user.id == OWNER_ID:
        help_text += (
            "\n*Owner Commands*\n"
            "/ping - System stats\n"
            "/reboot - Reboot VPS\n"
            "/auth `<id>` - Authorize user\n"
            "/deauth `<id>` - Remove user\n"
        )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_text,
        parse_mode='Markdown'
    )

# Main entry
async def post_init(application: Application):
    try:
        await application.bot.send_message(
            chat_id=OWNER_ID,
            text="Bot started successfully!\nUse /ping to check status."
        )
        print("[BOOT] Notification sent to owner.")
    except Exception as e:
        print(f"[BOOT] Failed to send boot message: {e}")

def main():
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stream", stream))
    application.add_handler(CommandHandler("streaminfo", streaminfo))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("reboot", reboot))
    application.add_handler(CommandHandler("auth", auth))
    application.add_handler(CommandHandler("deauth", deauth))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("[BOT] Starting polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
