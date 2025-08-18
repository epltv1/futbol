# Futbol Stream Bot

A Telegram bot in the `futbol` repository that streams M3U8 links to RTMP destinations with optional logo and text overlays.

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
1. Clone the repository: `git clone https://github.com/epltv1/futbol.git`
2. Navigate to the main branch: `cd futbol`
3. Install dependencies: `pip install -r requirements.txt`
4. Install FFmpeg on the VPS: `sudo apt-get install ffmpeg`
5. Update `config.py` with your bot token and Telegram ID.
6. Run the bot: `python bot.py`

## Deployment
See deployment instructions below.

## Requirements
- Python 3.8+
- FFmpeg
- SQLite (included with Python)
