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
            "-vf", "select=eq(n,0)",   # fixed escape
            "-q:v", "2",
            "-y",
            thumbnail_path
        ]
        try:
            subprocess.run(ffmpeg_cmd,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,
                           timeout=15)
            if os.path.exists(thumbnail_path):
                return thumbnail_path
            return None
        except Exception:
            return None

    def thumbnail_thread(self, m3u8_link, stream_id):
        self.generate_thumbnail(m3u8_link, stream_id)
        while not self.stop_threads.get(stream_id, False):
            self.generate_thumbnail(m3u8_link, stream_id)
            time.sleep(5)

    def start_stream(self, m3u8_link, rtmp_url, stream_key, stream_title):
        stream_id = str(uuid.uuid4())
        rtmp_destination = f"{rtmp_url.rstrip('/')}/{stream_key.lstrip('/')}"

        def build_ffmpeg_cmd():
            return [
                "ffmpeg",
                "-re",
                "-i", m3u8_link,
                "-c:v", "copy",
                "-c:a", "copy",
                "-f", "flv",
                "-loglevel", "error",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "30",
                "-timeout", "10000000",
                rtmp_destination
            ]

        def monitor_stream(stream_id, process, log_file_path):
            while stream_id in self.processes and not self.stop_threads.get(stream_id, False):
                process.poll()
                if process.returncode is not None:
                    try:
                        with open(log_file_path, "a") as log_file:
                            new_process = subprocess.Popen(build_ffmpeg_cmd(),
                                                          stdout=log_file,
                                                          stderr=log_file)
                        new_process.poll()
                        if new_process.returncode is not None:
                            with open(log_file_path, "r") as f:
                                error_log = f.read()
                            print(f"Failed to restart stream {stream_id}: {error_log}")
                            break
                        self.processes[stream_id]["process"] = new_process
                        print(f"Restarted FFmpeg process for stream {stream_id}")
                    except Exception as e:
                        print(f"Error restarting stream {stream_id}: {str(e)}")
                        break
                time.sleep(10)

        log_file_path = f"/tmp/{stream_id}_ffmpeg.log"
        try:
            # FIXED: removed the typo "log_file_pathoccupied"
            with open(log_file_path, "w") as log_file:
                process = subprocess.Popen(build_ffmpeg_cmd(),
                                          stdout=log_file,
                                          stderr=log_file)
            process.poll()
            if process.returncode is not None and process.returncode != 0:
                with open(log_file_path, "r") as f:
                    error_log = f.read()
                raise RuntimeError(f"FFmpeg failed to start: {error_log}")

            self.processes[stream_id] = {"process": process,
                                        "start_time": datetime.utcnow()}
            self.stop_threads[stream_id] = False

            thread = threading.Thread(target=self.thumbnail_thread,
                                      args=(m3u8_link, stream_id))
            thread.daemon = True
            thread.start()
            self.thumbnail_threads[stream_id] = thread   # fixed missing dot

            monitor_thread = threading.Thread(target=monitor_stream,
                                              args=(stream_id, process, log_file_path))
            monitor_thread.daemon = True
            monitor_thread.start()

            return stream_id

        except Exception as e:
            error_log = "No log file generated."
            if os.path.exists(log_file_path):
                with open(log_file_path, "r") as f:
                    error_log = f.read()
            raise RuntimeError(f"FFmpeg error: {str(e)}\nLog: {error_log}")

    def stop_stream(self, stream_id):
        if stream_id in self.processes:
            self.stop_threads[stream_id] = True
            if stream_id in self.thumbnail_threads:
                self.thumbnail_threads[stream_id].join(timeout=1)
                del self.thumbnail_threads[stream_id]
            del self.stop_threads[stream_id]

            self.processes[stream_id]["process"].terminate()
            try:
                self.processes[stream_id]["process"].wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.processes[stream_id]["process"].kill()
            del self.processes[stream_id]

            for path in [f"/tmp/{stream_id}_ffmpeg.log",
                         f"/tmp/{stream_id}_thumb.jpg"]:
                if os.path.exists(path):
                    os.remove(path)
            return True
        return False

    def get_stream_duration_request_duration(self, stream_id):
        if stream_id in self.processes:
            start_time = self.processes[stream_id]["start_time"]
            duration = (datetime.utcnow() - start_time).total_seconds()
            return f"{int(duration // 3600)}h {int((duration % 3600) // 60)}m {int(duration % 60)}s"
        return None
