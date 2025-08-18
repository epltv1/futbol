# bot.py
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import psutil
import time
import os
import subprocess
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

    # Extract parameters
    m3u8_link = args[0]
    rtmp_url = args[1]
    stream_key = args[2]
    stream_title = " ".join(args[3:])  # Allow stream_title with spaces

    # Validate inputs (check for non-empty strings)
    if not m3u8_link or not rtmp_url or not stream_key or not stream_title:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="M3U8 link, RTMP URL, stream key, and stream title cannot be empty."
        )
        return

    try:
        user_id = update.effective_user.id
        stream_id = stream_manager.start_stream(m3u8_link, rtmp_url, stream_key, stream_title)
        db.add_stream(stream_id, m3u8_link, rtmp_url, stream_key, stream_title, user_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream started with ID: {stream_id}"
        )
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to start stream: {str(e)}"
        )

# /streaminfo command
async def streaminfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    user_id = update.effective_user.id
    if not await is_authorized_user(update, context):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not authorized to use this command."
        )
        return

    # Owner sees all streams, others see only their own
    if user_id == OWNER_ID:
        streams = db.get_all_streams()
    else:
        streams = db.get_user_streams(user_id)

    if not streams:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No active streams."
        )
        return

    for stream in streams:
        stream_id, m3u8_link, _, _, stream_title, _, _ = stream
        duration = stream_manager.get_stream_duration(stream_id)
        if duration:
            thumbnail_path = f"/tmp/{stream_id}_thumb.jpg"
            message = f"Stream ID: {stream_id}\nTitle: {stream_title}\nDuration: {duration}"
            keyboard = [[InlineKeyboardButton("Stop", callback_data=f"stop_{stream_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if os.path.exists(thumbnail_path):
                with open(thumbnail_path, 'rb') as photo:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=photo,
                        caption=message,
                        reply_markup=reply_markup
                    )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"{message}\nWarning: Thumbnail not available.",
                    reply_markup=reply_markup
                )

# /stop command
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
    # Check if stream exists and user is allowed to stop it
    stream = db.get_stream(stream_id)
    if not stream:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream {stream_id} not found."
        )
        return
    if user_id != OWNER_ID and stream[5] != user_id:  # stream[5] is user_id
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"You can only stop your own streams."
        )
        return

    if stream_manager.stop_stream(stream_id):
        db.remove_stream(stream_id)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream {stream_id} stopped."
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Stream {stream_id} not found."
        )

# Inline button handler for stopping streams
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    if not await is_authorized_user(update, context):
        await query.message.edit_caption(caption="You are not authorized to perform this action.")
        return

    stream_id = query.data.replace("stop_", "")
    stream = db.get_stream(stream_id)
    if not stream:
        await query.message.edit_caption(caption=f"Stream {stream_id} not found.")
        return
    if user_id != OWNER_ID and stream[5] != user_id:  # stream[5] is user_id
        await query.message.edit_caption(caption="You can only stop your own streams.")
        return

    if stream_manager.stop_stream(stream_id):
        db.remove_stream(stream_id)
        await query.message.edit_caption(caption=f"Stream {stream_id} stopped.")
    else:
        await query.message.edit_caption(caption=f"Stream {stream_id} not found.")

# /ping command (owner only)
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="This command is restricted to the bot owner."
        )
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=response
    )

# /reboot command (owner only)
async def reboot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await delete_message(update, context)
    if update.effective_user.id != OWNER_ID:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="This command is restricted to the bot owner."
        )
        return

    try:
        # Stop all streams
        streams = db.get_all_streams()
        for stream in streams:
            stream_id = stream[0]
            stream_manager.stop_stream(stream_id)
            db.remove_stream(stream_id)
        
        # Initiate VPS reboot
        subprocess.run(["sudo", "reboot"], check=True)
        # Note: The bot will not send a message immediately after reboot
        # as it will be terminated during the reboot process.
        # The message will be sent after the bot restarts (handled in main()).
    except Exception as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Failed to reboot: {str(e)}"
        )

# /auth command
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

# /deauth command
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
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You are not authorized to use this command."
        )
        return

    help_text = """
Available Commands:
/start - Initialize the bot
/stream <m3u8_link> <rtmp_url> <stream_key> <stream_title> - Start a stream
/streaminfo - List your active streams with thumbnails and details
/stop <stream_id> - Stop a specific stream you started
/help - Show this help message
"""
    if update.effective_user.id == OWNER_ID:
        help_text += """
Owner-Only Commands:
/ping - Show bot uptime, CPU, storage, and RAM usage
/reboot - Stop all streams and reboot the VPS
/auth <telegram_id> - Authorize a user
/deauth <telegram_id> - Deauthorize a user
"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_text
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
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

    # Send "Boot complete" message to owner after bot starts
    async def send_boot_message():
        await application.bot.send_message(
            chat_id=OWNER_ID,
            text="Boot complete, enjoy using the bot"
        )

    # Schedule the boot message to run after bot initialization
    application.job_queue.run_once(lambda context: send_boot_message(), 1)

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
