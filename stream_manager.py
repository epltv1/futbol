# stream_manager.py
import subprocess
import uuid
import os
from datetime import datetime

class StreamManager:
    def __init__(self):
        self.processes = {}
        self.ffmpeg_path = "/home/fubtolx/ffmpeg"  # Update to "/home/fubtolx/futbol/bin/ffmpeg" if moved

    def start_stream(self, m3u8_link, rtmp_url, stream_key, stream_title):
        stream_id = str(uuid.uuid4())
        # Ensure rtmp_url ends with a slash and combine with stream_key
        rtmp_destination = f"{rtmp_url.rstrip('/')}/{stream_key.lstrip('/')}"
        
        # Build FFmpeg command for streaming
        ffmpeg_cmd = [
            self.ffmpeg_path,
            "-re",  # Read input at native frame rate
            "-i", m3u8_link,
            "-c", "copy",  # Copy video and audio without re-encoding
            "-f", "flv",
            "-loglevel", "verbose",  # Detailed logging for debugging
            rtmp_destination
        ]

        # Start FFmpeg process with detailed logging
        log_file_path = f"/tmp/{stream_id}_ffmpeg.log"
        print(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")  # Debug
        try:
            with open(log_file_path, "w") as log_file:
                process = subprocess.Popen(ffmpeg_cmd, stdout=log_file, stderr=log_file)
            # Check if process started successfully
            process.poll()
            if process.returncode is not None and process.returncode != 0:
                with open(log_file_path, "r") as f:
                    error_log = f.read()
                raise RuntimeError(f"FFmpeg failed to start: {error_log}")
            self.processes[stream_id] = {"process": process, "start_time": datetime.utcnow()}
            return stream_id
        except Exception as e:
            if os.path.exists(log_file_path):
                with open(log_file_path, "r") as f:
                    error_log = f.read()
            else:
                error_log = "No log file generated."
            print(f"FFmpeg error: {str(e)}\nLog: {error_log}")  # Debug
            raise RuntimeError(f"FFmpeg error: {str(e)}\nLog: {error_log}")

    def stop_stream(self, stream_id):
        if stream_id in self.processes:
            # Stop FFmpeg process
            self.processes[stream_id]["process"].terminate()
            try:
                self.processes[stream_id]["process"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.processes[stream_id]["process"].kill()
            del self.processes[stream_id]
            # Clean up log file
            log_file_path = f"/tmp/{stream_id}_ffmpeg.log"
            if os.path.exists(log_file_path):
                os.remove(log_file_path)
            return True
        return False

    def get_stream_duration(self, stream_id):
        if stream_id in self.processes:
            start_time = self.processes[stream_id]["start_time"]
            duration = (datetime.utcnow() - start_time).total_seconds()
            return f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m {int(duration % 60)}s"
        return None
