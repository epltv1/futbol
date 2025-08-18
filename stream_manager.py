# stream_manager.py
import subprocess
import uuid
import os
from datetime import datetime

class StreamManager:
    def __init__(self):
        self.processes = {}

    def start_stream(self, m3u8_link, rtmp_url, stream_key, stream_title, logo_url=None, text_overlay=None):
        stream_id = str(uuid.uuid4())
        rtmp_destination = f"{rtmp_url}/{stream_key}"
        
        # Build FFmpeg command
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", m3u8_link,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-f", "flv",
            rtmp_destination
        ]

        # Add logo overlay if provided
        if logo_url:
            # Download logo (assuming it's accessible)
            logo_path = f"/tmp/{stream_id}_logo.png"
            os.system(f"curl -o {logo_path} {logo_url}")
            ffmpeg_cmd.insert(-2, "-vf")
            ffmpeg_cmd.insert(-2, f"movie={logo_path}:format=png [logo]; [in][logo] overlay=W-w-10:10 [out]")

        # Add text overlay if provided
        if text_overlay:
            if logo_url:
                ffmpeg_cmd[-3] = f"{ffmpeg_cmd[-3].replace('[out]', '')},drawtext=text='{text_overlay}':fontcolor=white:fontsize=24:x=W-tw-10:y=H-th-10 [out]"
            else:
                ffmpeg_cmd.insert(-2, "-vf")
                ffmpeg_cmd.insert(-2, f"drawtext=text='{text_overlay}':fontcolor=white:fontsize=24:x=W-tw-10:y=H-th-10")

        # Start FFmpeg process
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.processes[stream_id] = {"process": process, "start_time": datetime.utcnow()}
        return stream_id

    def stop_stream(self, stream_id):
        if stream_id in self.processes:
            self.processes[stream_id]["process"].terminate()
            try:
                self.processes[stream_id]["process"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.processes[stream_id]["process"].kill()
            del self.processes[stream_id]
            # Clean up logo file if exists
            logo_path = f"/tmp/{stream_id}_logo.png"
            if os.path.exists(logo_path):
                os.remove(logo_path)
            return True
        return False

    def get_stream_duration(self, stream_id):
        if stream_id in self.processes:
            start_time = self.processes[stream_id]["start_time"]
            duration = (datetime.utcnow() - start_time).total_seconds()
            return f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m {int(duration % 60)}s"
        return None
