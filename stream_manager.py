# stream_manager.py
import subprocess
import uuid
import os
from datetime import datetime
import threading
import time

class StreamManager:
    def __init__(self):
        self.processes = {}
        self.thumbnail_threads = {}
        self.stop_threads = {}

    def generate_thumbnail(self, m3u8_link, stream_id):
        thumbnail_path = f"/tmp/{stream_id}_thumb.jpg"
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", m3u8_link,
            "-vframes", "1",
            "-vf", "select=eq(n\,0)",  # Capture first frame
            "-q:v", "2",  # High quality JPEG
            "-y",  # Overwrite existing file
            thumbnail_path
        ]
        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if os.path.exists(thumbnail_path):
                return thumbnail_path
            return None
        except Exception:
            return None

    def thumbnail_thread(self, m3u8_link, stream_id):
        while not self.stop_threads.get(stream_id, False):
            self.generate_thumbnail(m3u8_link, stream_id)
            time.sleep(5)  # Update thumbnail every 5 seconds

    def start_stream(self, m3u8_link, rtmp_url, stream_key, stream_title):
        stream_id = str(uuid.uuid4())
        # Ensure rtmp_url ends with a slash and combine with stream_key
        rtmp_destination = f"{rtmp_url.rstrip('/')}/{stream_key.lstrip('/')}"
        
        # Build FFmpeg command for streaming
        ffmpeg_cmd = [
            "ffmpeg",
            "-re",  # Read input at native frame rate
            "-i", m3u8_link,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-f", "flv",
            "-loglevel", "error",  # Log only errors
            rtmp_destination
        ]

        # Start FFmpeg process with detailed logging
        log_file = f"/tmp/{stream_id}_ffmpeg.log"
        try:
            with open(log_file, "w") as log_file:
                process = subprocess.Popen(ffmpeg_cmd, stdout
