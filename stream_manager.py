# stream_manager.py
import subprocess
import uuid
import os
from datetime import datetime

class StreamManager:
    def __init__(self):
        self.processes = {}

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
                process = subprocess.Popen(ffmpeg_cmd, stdout=log_file, stderr=log_file)
            # Check if process started successfully
            process.poll()
            if process.returncode is not None and process.returncode != 0:
                with open(log_file, "r") as f:
                    error_log = f.read()
                raise RuntimeError(f"FFmpeg failed to start: {error_log}")
            self.processes[stream_id] = {"process": process, "start_time": datetime.utcnow()}
            return stream_id
        except Exception as e:
            with open(log_file, "r") as f:
                error_log = f.read()
            raise RuntimeError(f"FFmpeg error: {str(e)}\nLog: {error_log}")

    def stop_stream(self, stream_id):
        if stream_id in self.processes:
            self.processes[stream_id]["process"].terminate()
            try:
                self.processes[stream_id]["process"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.processes[stream_id]["process"].kill()
            del self.processes[stream_id]
            # Clean up log file and thumbnail if exist
            for path in [f"/tmp/{stream_id}_ffmpeg.log", f"/tmp/{stream_id}_thumb.jpg"]:
                if os.path.exists(path):
                    os.remove(path)
            return True
        return False

    def get_stream_duration(self, stream_id):
        if stream_id in self.processes:
            start_time = self.processes[stream_id]["start_time"]
            duration = (datetime.utcnow() - start_time).total_seconds()
            return f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m {int(duration % 60)}s"
        return None

    def generate_thumbnail(self, m3u8_link, stream_id):
        thumbnail_path = f"/tmp/{stream_id}_thumb.jpg"
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", m3u8_link,
            "-vframes", "1",
            "-vf", "select=eq(n\,0)",  # Capture first frame
            "-q:v", "2",  # High quality JPEG
            thumbnail_path
        ]
        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if os.path.exists(thumbnail_path):
                return thumbnail_path
            return None
        except Exception:
            return None
