# bot.py
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import psutil
import time
import re
from config import BOT_TOKEN, OWNER_ID
from database import Database
from stream_manager import StreamManager

# Initialize database and stream manager
db = Database()
stream_manager = StreamManager()
start_time = time.time()

# Utility to check if user is authorized
async def is_authorized_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    return user_id == OWNER_ID or db.is_authorized(user_id)

# Auto-delete message
async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.delete()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this bot.")
        return
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Welcome to the Stream Bot! Use /help to see available commands.")

# /stream command
async def stream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return

    args = context.args
    if len(args) < 4:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /stream <m3u8_link> <rtmp_url> <stream_key> <stream_title> [logo_url] [text]")
        return

    m3u8_link, rtmp_url, stream_key, stream_title = args[:4]
    logo_url = args[4] if len(args) > 4 else None
    text_overlay = " ".join(args[5:]) if len(args) > 5 else None

    # Validate inputs (check for non-empty strings)
    if not m3u8_link or not rtmp_url or not stream_key or not stream_title:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="M3U8 link, RTMP URL, stream key, and stream title cannot be empty.")
        return

    try:
        stream_id = stream_manager.start_stream(m3u8_link, rtmp_url, stream_key, stream_title, logo_url, text_overlay)
        db.add_stream(stream_id, m3u8_link, rtmp_url, stream_key, stream_title, logo_url, text_overlay)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Stream started with ID: {stream_id}")
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Failed to start stream: {str(e)}")

# /streaminfo command
async def streaminfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return

    streams = db.get_all_streams()
    if not streams:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No active streams.")
        return

    message = "Active Streams:\n"
    for stream in streams:
        stream_id, _, _, _, stream_title, _, _, _ = stream
        duration = stream_manager.get_stream_duration(stream_id)
        if duration:
            keyboard = [[InlineKeyboardButton("Stop", callback_data=f"stop_{stream_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message += f"ID: {stream_id}\nTitle: {stream_title}\nDuration: {duration}\n\n"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            message = ""

# /stop command
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return

    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /stop <stream_id>")
        return

    stream_id = context.args[0]
    if stream_manager.stop_stream(stream_id):
        db.remove_stream(stream_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Stream {stream_id} stopped.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Stream {stream_id} not found.")

# Inline button handler for stopping streams
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await is_authorized_user(update, context):
        await query.message.edit_text(text="You are not authorized to perform this action.")
        return

    stream_id = query.data.replace("stop_", "")
    if stream_manager.stop_stream(stream_id):
        db.remove_stream(stream_id)
        await query.message.edit_text(text=f"Stream {stream_id} stopped.")
    else:
        await query.message.edit_text(text=f"Stream {stream_id} not found.")

# /ping command (owner only)
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="This command is restricted to the bot owner.")
        return

    # Calculate bot uptime
    uptime = time.time() - start_time
    uptime_str = f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"

    # Get CPU usage
    cpu_usage = psutil.cpu_percent()

    # Get storage (disk) usage in GB
    disk = psutil.disk_usage('/')
    disk_used = round(disk.used / (1024 ** 3), 2)  # Convert bytes to GB
    disk_total = round(disk.total / (1024 ** 3), 2)  # Convert bytes to GB

    # Get RAM usage in GB
    memory = psutil.virtual_memory()
    memory_used = round(memory.used / (1024 ** 3), 2)  # Convert bytes to GB
    memory_total = round(memory.total / (1024 ** 3), 2)  # Convert bytes to GB

    # Format response
    response = (
        f"Bot Uptime: {uptime_str}\n"
        f"CPU Usage: {cpu_usage}%\n"
        f"Storage: {disk_used} GB used / {disk_total} GB total\n"
        f"RAM: {memory_used} GB used / {memory_total} GB total"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# /auth command (owner only)
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="This command is restricted to the bot owner.")
        return

    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /auth <telegram_id>")
        return

    try:
        telegram_id = int(context.args[0])
        db.add_user(telegram_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"User {telegram_id} authorized.")
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid Telegram ID.")

# /deauth command (owner only)
async def deauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="This command is restricted to the bot owner.")
        return

    if not context.args:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /deauth <telegram_id>")
        return

    try:
        telegram_id = int(context.args[0])
        db.remove_user(telegram_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"User {telegram_id} deauthorized.")
    except ValueError:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid Telegram ID.")

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if not await is_authorized_user(update, context):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You are not authorized to use this command.")
        return

    help_text = """
Available Commands:
/start - Initialize the bot
/stream <m3u8_link> <rtmp_url> <stream_key> <stream_title> [logo_url] [text] - Start a stream
/streaminfo - List all active streams with details
/stop <stream_id> - Stop a specific stream
/help - Show this help message
"""
    if update.effective_user.id == OWNER_ID:
        help_text += """
Owner-Only Commands:
/ping - Show bot uptime, CPU, storage, and RAM usage
/auth <telegram_id> - Authorize a user
/deauth <telegram_id> - Deauthorize a user
"""
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stream", stream))
    application.add_handler(CommandHandler("streaminfo", streaminfo))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("ping", ping))
    application.add_handler(CommandHandler("auth", auth))
    application.add_handler(CommandHandler("deauth", deauth))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
