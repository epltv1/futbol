# Futbol Stream Bot

A Telegram bot in the `futbol` repository that streams M3U8 links to RTMP destinations with optional logo and text overlays.

## Features
- `/start`: Welcome message.
- `/stream <m3u8_link> <rtmp_url> <stream_key> <stream_title> [logo_url] [text]`: Start a stream with optional logo (top-right) and/or text (bottom-right) overlays.
- `/streaminfo`: List active streams with their ID, title, duration, and inline stop buttons.
- `/stop <stream_id>`: Stop a specific stream.
- `/ping`: Show bot uptime, CPU, storage, and RAM usage (owner only).
- `/auth <telegram_id>`: Authorize a user (owner only).
- `/deauth <telegram_id>`: Deauthorize a user (owner only).
- `/help`: List all commands.

## Setup
1. Clone the repository: `git clone https://github.com/epltv1/futbol.git`
2. Navigate to the main branch: `cd futbol`
3. Install dependencies: `pip install -r requirements.txt`
4. Install system dependencies on the VPS: See deployment steps below.
5. Update `config.py` with your bot token and Telegram ID.
6. Run the bot: `python bot.py`

## Requirements
- Python 3.8+
- FFmpeg
- SQLite (included with Python)
- `curl` (for downloading logos)

## Stream Command Details
The `/stream` command supports flexible overlays:
- **Mandatory**: `m3u8_link`, `rtmp_url`, `stream_key`, `stream_title`.
- **Optional**: `logo_url` (image URL for top-right logo), `text` (text for bottom-right overlay).
- Examples:
  - Both logo and text: `/stream <m3u8_link> <rtmp_url> <stream_key> Test stream https://example.com/logo.png Test`
  - Text only: `/stream <m3u8_link> <rtmp_url> <stream_key> Test stream Test`
  - Logo only: `/stream <m3u8_link> <rtmp_url> <stream_key> Test stream https://example.com/logo.png`
  - Neither: `/stream <m3u8_link> <rtmp_url> <stream_key> Test stream`

## Deployment to VPS
Follow these steps to deploy the bot on an Ubuntu-based VPS:

### Prerequisites
- A VPS running Ubuntu (e.g., DigitalOcean, AWS, Linode).
- SSH access to the VPS.
- A Telegram bot token from BotFather (create via `@BotFather` on Telegram).
- Your Telegram ID (use `@userinfobot` on Telegram to get it).

### Steps
1. **Connect to the VPS**:
   ```bash
   ssh username@your-vps-ip
