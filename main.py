#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Downloader — pywebview App
后端用 Flask，进度推送用 SSE（无 WebSocket 依赖）
"""

import sys
import os
import json
import queue
import threading
import subprocess
import time
import uuid
from pathlib import Path
from flask import Flask, send_from_directory, request, jsonify, Response, stream_with_context

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
STATIC   = BASE_DIR / "static"

app = Flask(__name__, static_folder=str(STATIC))

# ── yt-dlp 自动更新状态
_ytdlp_update_status = {"state": "idle", "msg": ""}   # idle / updating / done / error


def _run_ytdlp_update():
    """后台线程：运行 yt-dlp -U 并更新状态"""
    global _ytdlp_update_status
    _ytdlp_update_status = {"state": "updating", "msg": "正在检查更新…"}
    try:
        ytdlp = find_ytdlp()
        # yt-dlp -U 自我更新（本地二进制模式）
        result = subprocess.run(
            ytdlp + ["-U"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60
        )
        output = (result.stdout + result.stderr).strip()
        if "up to date" in output or "已是最新" in output:
            ver = ""
            import re
            m = re.search(r"stable@([\d.]+)", output)
            if m:
                ver = f" (v{m.group(1)})"
            _ytdlp_update_status = {"state": "done", "msg": f"yt-dlp 已是最新{ver}"}
        elif result.returncode == 0:
            _ytdlp_update_status = {"state": "done", "msg": f"yt-dlp 更新成功！{output[:80]}"}
        else:
            _ytdlp_update_status = {"state": "error", "msg": f"更新失败: {output[:120]}"}
    except Exception as e:
        _ytdlp_update_status = {"state": "error", "msg": f"更新出错: {e}"}


# ── 站酷专用解析（yt-dlp 没有站酷提取器，需手动解析）
def resolve_zcool(url: str):
    """从站酷作品页解析出真实视频 URL 列表，返回 (video_urls, title)"""
    import urllib.request, json, re
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.zcool.com.cn",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        html = r.read().decode("utf-8", errors="replace")

    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("无法解析站酷页面，请检查链接是否正确")

    data  = json.loads(m.group(1))
    props = data["props"]["pageProps"]
    d     = props.get("data", {})
    title = d.get("title", "zcool_video")
    # 清理文件名中的非法字符
    title = re.sub(r'[\\/:*?"<>|]', '_', title)

    videos = d.get("productVideos", [])
    urls   = [v["url"] for v in videos if v.get("url")]

    # 从 editorJson 兜底捞
    if not urls:
        editor = d.get("editorJson", "")
        if isinstance(editor, str):
            found = re.findall(
                r'https?://video\.zcool\.cn/[^\s"\']+\.mp4[^\s"\']*', editor
            )
            urls = [u for u in found if "vframe" not in u]

    if not urls:
        raise ValueError("未找到视频资源，该作品可能不含视频或需要登录")

    return urls, title


# ── 每个下载任务对应一个 queue
_sessions: dict[str, queue.Queue] = {}
_procs:    dict[str, subprocess.Popen] = {}
_lock = threading.Lock()


def find_ytdlp():
    import platform
    fname = "yt-dlp.exe" if platform.system() == "Windows" else "yt-dlp"
    local = BASE_DIR / fname
    if local.exists():
        return [str(local)]
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return [sys.executable, "-m", "yt_dlp"]
    import shutil
    p = shutil.which("yt-dlp")
    if p:
        return [p]
    raise FileNotFoundError("未找到 yt-dlp，请联系开发者")


def find_ffmpeg():
    import platform
    fname = "ffmpeg.exe" if platform.system() == "Windows" else "ffmpeg"
    local = BASE_DIR / fname
    if local.exists():
        return str(local)
    import shutil
    return shutil.which("ffmpeg") or ""


# ── 静态页面
@app.route("/")
def index():
    return send_from_directory(str(STATIC), "index.html")


@app.route("/logo")
def logo():
    logo_path = BASE_DIR / "logo.jpg"
    if logo_path.exists():
        from flask import send_file
        return send_file(str(logo_path), mimetype="image/jpeg")
    return "", 404


# ── yt-dlp 更新接口
@app.route("/ytdlp-update", methods=["POST"])
def ytdlp_update():
    """手动触发或查询 yt-dlp 更新"""
    if _ytdlp_update_status["state"] != "updating":
        threading.Thread(target=_run_ytdlp_update, daemon=True).start()
    return jsonify(ok=True, status=_ytdlp_update_status)


@app.route("/ytdlp-status", methods=["GET"])
def ytdlp_status():
    """查询 yt-dlp 更新状态"""
    return jsonify(_ytdlp_update_status)


# ── 弹出文件夹选择对话框
@app.route("/pick-folder", methods=["POST"])
def pick_folder():
    """调用 pywebview 原生文件夹选择对话框，返回用户选中的路径"""
    import webview
    wins = webview.windows
    if not wins:
        return jsonify(ok=False, path=None)
    result = wins[0].create_file_dialog(
        webview.FOLDER_DIALOG,
        allow_multiple=False
    )
    if result and len(result) > 0:
        return jsonify(ok=True, path=result[0])
    return jsonify(ok=True, path=None)


# ── 打开 Finder
@app.route("/open-folder", methods=["POST"])
def open_folder():
    data   = request.get_json(silent=True) or {}
    folder = os.path.expanduser(data.get("folder", "~/Downloads"))
    folder = os.path.abspath(folder)
    if os.path.isdir(folder):
        import platform
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", folder])
        else:
            subprocess.Popen(["open", "-a", "Finder", folder])
    return jsonify(ok=True)


# ── 开始下载（返回 session_id）
@app.route("/start", methods=["POST"])
def start_download():
    data     = request.get_json(silent=True) or {}
    url      = data.get("url", "").strip()
    save_dir = os.path.expanduser(data.get("save_dir", "~/Downloads"))

    if not url:
        return jsonify(ok=False, error="URL 不能为空"), 400

    os.makedirs(save_dir, exist_ok=True)

    # ── 站酷专用下载路径
    if "zcool.com.cn" in url:
        try:
            video_urls, title = resolve_zcool(url)
        except Exception as e:
            return jsonify(ok=False, error=f"站酷解析失败：{e}"), 400

        ffmpeg = find_ffmpeg()
        sid = str(uuid.uuid4())
        q   = queue.Queue()
        with _lock:
            _sessions[sid] = q

        def run_zcool():
            try:
                for i, vurl in enumerate(video_urls):
                    suffix = f"_{i+1}" if len(video_urls) > 1 else ""
                    out_path = os.path.join(save_dir, f"{title}{suffix}.mp4")
                    q.put({"type": "log", "line": f"[站酷] 开始下载: {title}{suffix}.mp4"})
                    ytdlp = find_ytdlp()
                    cmd = ytdlp + [
                        "--no-playlist", "--newline",
                        "--no-check-certificates",
                        "--user-agent",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "--add-header", "Referer:https://www.zcool.com.cn",
                        "-o", out_path,
                        vurl,
                    ]
                    if ffmpeg:
                        cmd += ["--ffmpeg-location", ffmpeg]
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, encoding="utf-8", errors="replace"
                    )
                    with _lock:
                        _procs[sid] = proc
                    for line in proc.stdout:
                        line = line.rstrip()
                        if not line:
                            continue
                        payload = {"type": "log", "line": line}
                        if "[download]" in line and "%" in line:
                            try:
                                parts = line.split()
                                pct   = float(parts[1].rstrip("%"))
                                speed = eta = size = ""
                                for j, p in enumerate(parts):
                                    if p == "at"  and j+1 < len(parts): speed = parts[j+1]
                                    if p == "ETA" and j+1 < len(parts): eta   = parts[j+1]
                                    if p == "of"  and j+1 < len(parts): size  = parts[j+1]
                                payload = {"type": "progress", "pct": pct,
                                           "speed": speed, "eta": eta, "size": size, "line": line}
                            except Exception:
                                pass
                        q.put(payload)
                    proc.wait()
                    if proc.returncode not in (0,):
                        q.put({"type": "error", "msg": "下载失败，请检查网络或视频权限"})
                        q.put(None)
                        return
                q.put({"type": "done", "save_dir": save_dir})
            except Exception as e:
                q.put({"type": "error", "msg": str(e)})
            finally:
                q.put(None)
                with _lock:
                    _procs.pop(sid, None)

        threading.Thread(target=run_zcool, daemon=True).start()
        return jsonify(ok=True, sid=sid)

    # ── 通用 yt-dlp 下载路径
    try:
        ytdlp = find_ytdlp()
    except FileNotFoundError as e:
        return jsonify(ok=False, error=str(e)), 500

    ffmpeg = find_ffmpeg()
    cmd = ytdlp + [
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-playlist", "--newline",
        "--no-check-certificates",
        "--user-agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "--add-header", f"Referer:{url}",
        "-o", os.path.join(save_dir, "%(title)s.%(ext)s"),
        url,
    ]
    if ffmpeg:
        cmd += ["--ffmpeg-location", ffmpeg]

    sid = str(uuid.uuid4())
    q   = queue.Queue()
    with _lock:
        _sessions[sid] = q

    def run():
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace"
            )
            with _lock:
                _procs[sid] = proc

            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                payload = {"type": "log", "line": line}
                if "[download]" in line and "%" in line:
                    try:
                        parts = line.split()
                        pct   = float(parts[1].rstrip("%"))
                        speed = eta = size = ""
                        for i, p in enumerate(parts):
                            if p == "at"  and i+1 < len(parts): speed = parts[i+1]
                            if p == "ETA" and i+1 < len(parts): eta   = parts[i+1]
                            if p == "of"  and i+1 < len(parts): size  = parts[i+1]
                        payload = {"type": "progress", "pct": pct,
                                   "speed": speed, "eta": eta, "size": size, "line": line}
                    except Exception:
                        pass
                elif "[Merger]" in line or "Merging" in line:
                    payload = {"type": "merging", "line": line}
                elif "ExtractAudio" in line:
                    payload = {"type": "audio", "line": line}
                q.put(payload)

            proc.wait()
            rc = proc.returncode
            if rc == 0:
                q.put({"type": "done", "save_dir": save_dir})
            elif rc in (-15, -9, 1):
                q.put({"type": "stopped"})
            else:
                q.put({"type": "error", "msg": "下载失败，请检查链接或网络"})
        except Exception as e:
            q.put({"type": "error", "msg": str(e)})
        finally:
            q.put(None)   # 结束信号
            with _lock:
                _procs.pop(sid, None)

    threading.Thread(target=run, daemon=True).start()
    return jsonify(ok=True, sid=sid)


# ── 停止下载
@app.route("/stop", methods=["POST"])
def stop_download():
    data = request.get_json(silent=True) or {}
    sid  = data.get("sid", "")
    with _lock:
        proc = _procs.get(sid)
    if proc and proc.poll() is None:
        proc.terminate()
    return jsonify(ok=True)


# ── SSE 进度流
@app.route("/progress/<sid>")
def progress(sid):
    def generate():
        with _lock:
            q = _sessions.get(sid)
        if not q:
            yield "data: {\"type\":\"error\",\"msg\":\"session not found\"}\n\n"
            return
        while True:
            try:
                msg = q.get(timeout=30)
            except queue.Empty:
                yield ": keep-alive\n\n"
                continue
            if msg is None:
                break
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
        with _lock:
            _sessions.pop(sid, None)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


# ── 启动
def start_flask(port):
    app.run(host="127.0.0.1", port=port, debug=False,
            use_reloader=False, threaded=True)


def main():
    PORT = 7788
    threading.Thread(target=start_flask, args=(PORT,), daemon=True).start()

    # 等待 Flask 就绪
    import urllib.request
    for _ in range(40):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/", timeout=1)
            break
        except Exception:
            time.sleep(0.2)

    # 启动时后台静默更新 yt-dlp
    threading.Thread(target=_run_ytdlp_update, daemon=True).start()

    import webview
    webview.create_window(
        "Video Downloader",
        url=f"http://127.0.0.1:{PORT}/",
        width=680,
        height=720,
        min_size=(600, 600),
        resizable=True,
        background_color="#0F0F13",
    )
    webview.start(debug=False)


if __name__ == "__main__":
    main()
