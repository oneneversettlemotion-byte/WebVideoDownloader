#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Downloader — Flask + WebSocket 后端
"""

import os
import sys
import json
import signal
import subprocess
import threading
import webbrowser
from pathlib import Path

from flask import Flask, send_from_directory, request, jsonify
from flask_sock import Sock

BASE_DIR  = Path(__file__).parent
STATIC    = BASE_DIR / "static"
app       = Flask(__name__, static_folder=str(STATIC))
sock      = Sock(app)

# 当前下载进程（全局，只允许一个）
_proc_lock  = threading.Lock()
_active_proc = None


def find_ytdlp():
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--version"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]
    import shutil
    p = shutil.which("yt-dlp")
    if p:
        return [p]
    raise FileNotFoundError("yt-dlp not found")


# ── 静态文件 ─────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(str(STATIC), "index.html")


@app.route("/open-folder", methods=["POST"])
def open_folder():
    data = request.get_json(silent=True) or {}
    folder = data.get("folder", str(Path.home() / "Downloads"))
    folder = os.path.expanduser(folder)
    if os.path.isdir(folder):
        subprocess.run(["open", folder])
    return jsonify(ok=True)


# ── WebSocket 下载 ───────────────────────────────────────────
@sock.route("/ws")
def ws_download(ws):
    global _active_proc

    raw = ws.receive()
    try:
        msg = json.loads(raw)
    except Exception:
        ws.send(json.dumps({"type": "error", "msg": "invalid message"}))
        return

    action = msg.get("action")

    # ── 停止
    if action == "stop":
        with _proc_lock:
            if _active_proc and _active_proc.poll() is None:
                _active_proc.terminate()
        ws.send(json.dumps({"type": "stopped"}))
        return

    # ── 下载
    if action != "download":
        return

    url      = msg.get("url", "").strip()
    save_dir = os.path.expanduser(msg.get("save_dir", "~/Downloads"))

    if not url:
        ws.send(json.dumps({"type": "error", "msg": "URL 不能为空"}))
        return
    if not os.path.isdir(save_dir):
        try:
            os.makedirs(save_dir, exist_ok=True)
        except Exception as e:
            ws.send(json.dumps({"type": "error", "msg": f"目录无效: {e}"}))
            return

    try:
        cmd = find_ytdlp()
    except FileNotFoundError as e:
        ws.send(json.dumps({"type": "error", "msg": str(e)}))
        return

    # 优先使用项目目录内的 ffmpeg，其次找系统 ffmpeg
    import shutil
    local_ffmpeg = BASE_DIR / "ffmpeg"
    if local_ffmpeg.exists():
        ffmpeg_path = str(local_ffmpeg)
    else:
        ffmpeg_path = shutil.which("ffmpeg") or ""

    cmd += [
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--newline",
        "--no-check-certificates",
        "-o", os.path.join(save_dir, "%(title)s.%(ext)s"),
        url,
    ]
    if ffmpeg_path:
        cmd += ["--ffmpeg-location", ffmpeg_path]

    ws.send(json.dumps({"type": "start"}))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace"
    )
    with _proc_lock:
        _active_proc = proc

    try:
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue

            payload = {"type": "log", "line": line}

            # 解析进度
            if "[download]" in line and "%" in line:
                try:
                    parts  = line.split()
                    pct    = float(parts[1].rstrip("%"))
                    speed  = ""
                    eta    = ""
                    size   = ""
                    for i, p in enumerate(parts):
                        if p == "at" and i+1 < len(parts):
                            speed = parts[i+1]
                        if p == "ETA" and i+1 < len(parts):
                            eta = parts[i+1]
                        if p == "of" and i+1 < len(parts):
                            size = parts[i+1]
                    payload.update({
                        "type":  "progress",
                        "pct":   pct,
                        "speed": speed,
                        "eta":   eta,
                        "size":  size,
                        "line":  line,
                    })
                except Exception:
                    pass
            elif "[Merger]" in line or "Merging" in line:
                payload.update({"type": "merging"})
            elif "ExtractAudio" in line:
                payload.update({"type": "audio"})

            try:
                ws.send(json.dumps(payload))
            except Exception:
                break

        proc.wait()
        rc = proc.returncode
        if rc == 0:
            ws.send(json.dumps({"type": "done", "save_dir": save_dir}))
        elif rc in (-15, -9):
            ws.send(json.dumps({"type": "stopped"}))
        else:
            ws.send(json.dumps({"type": "error", "msg": "下载失败，请检查链接或网络"}))
    except Exception as e:
        try:
            ws.send(json.dumps({"type": "error", "msg": str(e)}))
        except Exception:
            pass
    finally:
        with _proc_lock:
            _active_proc = None


# ── 启动 ─────────────────────────────────────────────────────
def open_browser(port):
    import time; time.sleep(0.8)
    webbrowser.open(f"http://127.0.0.1:{port}")


if __name__ == "__main__":
    port = 7788
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))
    # 仅在非 App 模式（直接命令行运行）时自动打开浏览器
    if not os.environ.get("VDAPP_MODE"):
        t = threading.Thread(target=open_browser, args=(port,), daemon=True)
        t.start()
    print(f"✅ Video Downloader 已启动: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
