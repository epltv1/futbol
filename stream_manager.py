# stream_manager.py
import subprocess
import uuid
import os
from datetime import datetime
import shlex

class StreamManager:
    def __init__(self):
        self.processes = {}

    def start_stream(self, m3u8_link, rtmp_url, stream_key, stream_title, logo_url=None, text_overlay=None):
        stream_id = str(uuid.uuid4())
        # Ensure rtmp_url ends with a slash and combine with stream_key
        rtmp_destination = f"{rtmp_url.rstrip('/')}/{stream_key.lstrip('/')}"
        
        # Build FFmpeg command
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

        # Add logo overlay if provided
        if logo_url:
            logo_path = f"/tmp/{stream_id}_logo.png"
            os.system(f"curl -s -o {logo_path} {logo_url}")
            if os.path.exists(logo_path):
                ffmpeg_cmd.insert(-2, "-vf")
                ffmpeg_cmd.insert(-2, f"movie={logo_path}:format=png [logo]; [in][logo] overlay=W-w-10:10 [out]")
            else:
                raise ValueError(f"Failed to download logo from {logo_url}")

        # Add text overlay if provided
        if text_overlay:
            # Escape special characters in text_overlay
            text_overlay = shlex.quote(text_overlay.strip())
            if logo_url:
                ffmpeg_cmd[-3] = f"{ffmpeg_cmd[-3].replace('[out]', '')},drawtext=text={text_overlay}:fontcolor=white:fontsize=24:x=W-tw-10:y=H-th-10 [out]"
            else:
                ffmpeg_cmd.insert(-2, "-vf")
                ffmpeg_cmd.insert(-2, f"drawtext=text={text_overlay}:fontcolor=white:fontsize=24:x=W-tw-10:y=H-th-10")

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
            # Clean up logo file and log file if they exist
            logo_path = f"/tmp/{stream_id}_logo.png"
            log_path = f"/tmp/{stream_id}_ffmpeg.log"
            for path in [logo_path, log_path]:
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
