# Telegram Stream Bot

A Telegram bot that streams M3U8 links to RTMP destinations with optional logo and text overlays.

## Features
- `/start`: Welcome message.
- `/stream <m3u8_link> <rtmp_url> <stream_key> <stream_title> [logo_url] [text]`: Start a stream with overlays.
- `/streaminfo`: List active streams with inline stop buttons.
- `/stop <stream_id>`: Stop a specific stream.
- `/ping`: Show bot uptime and system resources (owner only).
- `/auth <telegram_id>`: Authorize a user (owner only).
- `/deauth <telegram_id>`: Deauthorize a user (owner only).
- `/help`: List all commands.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Install FFmpeg on the VPS: `sudo apt-get install ffmpeg`
3. Update `config.py` with your bot token and Telegram ID.
4. Run the bot: `python bot.py`

## Deployment
See deployment instructions below.

## Requirements
- Python 3.8+
- FFmpeg
- SQLite (included with Python)
