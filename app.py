#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Video Downloader — Modern Gradient UI
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import threading
import os
import sys
import subprocess
import platform

# ── 颜色 ──────────────────────────────────────────────────────
C = {
    "bg":       "#F2F0ED",
    "surface":  "#FFFFFF",
    "border":   "#E4E2DE",
    "text":     "#1A1A1A",
    "text2":    "#6B6B70",
    "text3":    "#BCBCC0",
    "accent":   "#7C3AED",   # 紫
    "accent_h": "#6D28D9",
    "accent_l": "#EDE9FE",   # 浅紫背景
    "pink":     "#EC4899",
    "danger":   "#EF4444",
    "success":  "#10B981",
    "prog_bg":  "#E4E2DE",
    "log_bg":   "#FAF9F7",
    "log_fg":   "#52525B",
}

def _font(*args):
    if platform.system() == "Darwin":
        name = "-apple-system"
    else:
        name = "Segoe UI" if platform.system() == "Windows" else "Helvetica Neue"
    return (name,) + args


def find_ytdlp():
    try:
        r = subprocess.run([sys.executable, "-m", "yt_dlp", "--version"],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return [sys.executable, "-m", "yt_dlp"]
    except Exception:
        pass
    import shutil
    p = shutil.which("yt-dlp")
    if p:
        return [p]
    raise FileNotFoundError("未找到 yt-dlp，请先运行: pip3 install yt-dlp")


# ── 胶囊输入框 ────────────────────────────────────────────────
class PillEntry(tk.Frame):
    def __init__(self, parent, textvariable=None, placeholder="", **kw):
        super().__init__(parent, bg=C["surface"],
                         highlightbackground=C["border"],
                         highlightthickness=1, bd=0)
        self._ph    = placeholder
        self._var   = textvariable or tk.StringVar()
        self._ph_on = False
        self.entry  = tk.Entry(
            self, textvariable=self._var,
            bg=C["surface"], fg=C["text"],
            insertbackground=C["text"],
            relief="flat", bd=0,
            font=_font(13), **kw
        )
        self.entry.pack(fill="x", padx=16, ipady=12)
        if placeholder:
            self._set_ph()
            self.entry.bind("<FocusIn>",  self._on_in)
            self.entry.bind("<FocusOut>", self._on_out)

    def _set_ph(self):
        if not self._var.get():
            self.entry.configure(fg=C["text3"])
            self.entry.insert(0, self._ph)
            self._ph_on = True

    def _on_in(self, _=None):
        if self._ph_on:
            self.entry.delete(0, "end")
            self.entry.configure(fg=C["text"])
            self._ph_on = False
        self.configure(highlightbackground=C["accent"])

    def _on_out(self, _=None):
        self.configure(highlightbackground=C["border"])
        if not self._var.get():
            self._set_ph()

    def get(self):
        return "" if self._ph_on else self._var.get()

    def clear(self):
        self._var.set("")
        self.entry.configure(fg=C["text3"])
        self._set_ph()


# ── 圆角按钮（Canvas 实现）───────────────────────────────────
class PillButton(tk.Canvas):
    def __init__(self, parent, text, command,
                 bg="#7C3AED", fg="#FFFFFF", hover="#6D28D9",
                 px=36, py=12, r=22, font=None):
        self._bg   = bg
        self._hbg  = hover
        self._fg   = fg
        self._fn   = font or _font(13, "bold")
        self._cmd  = command
        self._txt  = text
        self._r    = r
        self._on   = True

        f  = tkfont.Font(font=self._fn)
        tw = f.measure(text)
        th = f.metrics("linespace")
        self._W = int(tw) + px * 2
        self._H = int(th) + py * 2

        try:
            pbg = parent.cget("bg")
        except Exception:
            pbg = C["bg"]

        super().__init__(parent,
                         width=self._W, height=self._H,
                         bg=pbg, bd=0, highlightthickness=0,
                         cursor="hand2")
        self._redraw()
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>",    self._enter)
        self.bind("<Leave>",    self._leave)

    def _rr(self, x1, y1, x2, y2, r, fill):
        kw = dict(fill=fill, outline=fill)
        self.create_arc(x1,     y1,     x1+2*r, y1+2*r, start=90,  extent=90,  **kw)
        self.create_arc(x2-2*r, y1,     x2,     y1+2*r, start=0,   extent=90,  **kw)
        self.create_arc(x1,     y2-2*r, x1+2*r, y2,     start=180, extent=90,  **kw)
        self.create_arc(x2-2*r, y2-2*r, x2,     y2,     start=270, extent=90,  **kw)
        self.create_rectangle(x1+r, y1,   x2-r, y2,   **kw)
        self.create_rectangle(x1,   y1+r, x2,   y2-r, **kw)

    def _redraw(self, col=None):
        c = col or self._bg
        self.delete("all")
        self._rr(0, 0, self._W, self._H, self._r, c)
        self.create_text(self._W//2, self._H//2,
                         text=self._txt, fill=self._fg, font=self._fn)

    def _click(self, _=None):
        if self._on:
            self._cmd()

    def _enter(self, _=None):
        if self._on:
            self._redraw(self._hbg)

    def _leave(self, _=None):
        self._redraw(self._bg if self._on else "#C4C4C8")

    def enable(self):
        self._on = True
        self.configure(cursor="hand2")
        self._redraw()

    def disable(self):
        self._on = False
        self.configure(cursor="arrow")
        self._redraw("#C4C4C8")


# ── 主应用 ───────────────────────────────────────────────────
class App:
    def __init__(self, root: tk.Tk):
        self.root  = root
        self.root.title("Video Downloader")
        self.root.resizable(False, False)
        self.root.configure(bg=C["bg"])

        self.save_dir    = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.downloading = False
        self._proc       = None

        self._ui()
        self._center(660, 580)

    def _center(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    # ── Hero banner ──────────────────────────────────────────
    def _hero(self):
        cv = tk.Canvas(self.root, width=660, height=116,
                       bd=0, highlightthickness=0, bg=C["bg"])
        cv.pack(fill="x")

        # 渐变背景 bar（底部细条，紫→粉）
        steps = 80
        for i in range(steps):
            t = i / steps
            r = int(0xC0 + (0xEC - 0xC0) * t)
            g = int(0x84 + (0x48 - 0x84) * t)
            b = int(0xFC + (0x99 - 0xFC) * t)
            color = f"#{r:02X}{g:02X}{b:02X}"
            x0 = int(660 * i / steps)
            x1 = int(660 * (i+1) / steps) + 1
            cv.create_rectangle(x0, 100, x1, 116, fill=color, outline=color)

        # 标题
        cv.create_text(32, 44, text="Video Downloader",
                       font=_font(24, "bold"), fill=C["text"], anchor="w")
        cv.create_text(32, 76, text="YouTube · Bilibili · Vimeo · Behance · 设计素材站",
                       font=_font(12), fill=C["text2"], anchor="w")

        # 装饰渐变球
        for x, y, s, col in [(596, 18, 52, "#C084FC"),
                              (624, 56, 48, "#F472B6"),
                              (568, 60, 32, "#818CF8")]:
            cv.create_oval(x-s//2, y-s//2, x+s//2, y+s//2,
                           fill=col, outline=col)

    # ── 整体 UI ──────────────────────────────────────────────
    def _ui(self):
        self._hero()

        body = tk.Frame(self.root, bg=C["bg"])
        body.pack(fill="both", padx=28, pady=0)

        # -- URL 输入
        lf = tk.Frame(body, bg=C["bg"])
        lf.pack(fill="x", pady=(10, 4))
        tk.Label(lf, text="视频链接", bg=C["bg"],
                 fg=C["text2"], font=_font(11)).pack(side="left")

        url_row = tk.Frame(body, bg=C["bg"])
        url_row.pack(fill="x")
        self._url_var = tk.StringVar()
        self.url_box  = PillEntry(url_row,
                                   textvariable=self._url_var,
                                   placeholder="粘贴视频链接，按 Enter 或点击开始下载……")
        self.url_box.pack(side="left", fill="x", expand=True)
        self.url_box.entry.bind("<Return>", lambda _: self._start())

        tk.Button(url_row, text="✕",
                  bg=C["bg"], fg=C["text3"],
                  activebackground=C["bg"], activeforeground=C["text2"],
                  relief="flat", bd=0, cursor="hand2",
                  font=_font(16), command=self.url_box.clear
                  ).pack(side="left", padx=(8, 0))

        # -- 保存位置
        tk.Label(body, text="保存位置", bg=C["bg"],
                 fg=C["text2"], font=_font(11)).pack(anchor="w", pady=(16, 4))

        dir_card = tk.Frame(body, bg=C["surface"],
                            highlightbackground=C["border"],
                            highlightthickness=1, bd=0)
        dir_card.pack(fill="x")
        row = tk.Frame(dir_card, bg=C["surface"])
        row.pack(fill="x", padx=14, pady=10)
        tk.Label(row, textvariable=self.save_dir,
                 bg=C["surface"], fg=C["text"],
                 font=_font(12), anchor="w"
                 ).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="更改",
                  bg=C["surface"], fg=C["accent"],
                  activebackground=C["surface"], activeforeground=C["accent_h"],
                  relief="flat", bd=0, cursor="hand2",
                  font=_font(12, "bold"),
                  command=self._choose_dir
                  ).pack(side="right")

        # -- 进度
        prog_card = tk.Frame(body, bg=C["surface"],
                             highlightbackground=C["border"],
                             highlightthickness=1, bd=0)
        prog_card.pack(fill="x", pady=(14, 0))
        pi = tk.Frame(prog_card, bg=C["surface"])
        pi.pack(fill="x", padx=16, pady=12)

        row2 = tk.Frame(pi, bg=C["surface"])
        row2.pack(fill="x")
        self.status_lbl = tk.Label(row2, text="准备就绪",
                                   bg=C["surface"], fg=C["text2"],
                                   font=_font(11), anchor="w")
        self.status_lbl.pack(side="left")
        self.pct_lbl = tk.Label(row2, text="",
                                bg=C["surface"], fg=C["accent"],
                                font=_font(11, "bold"), anchor="e")
        self.pct_lbl.pack(side="right")

        sty = ttk.Style()
        sty.theme_use("clam")
        sty.configure("P.Horizontal.TProgressbar",
                      troughcolor=C["prog_bg"], background=C["accent"],
                      bordercolor=C["prog_bg"], lightcolor=C["accent"],
                      darkcolor=C["accent"], thickness=8)
        self.progress = ttk.Progressbar(pi, orient="horizontal",
                                        style="P.Horizontal.TProgressbar",
                                        mode="determinate")
        self.progress.pack(fill="x", pady=(8, 0))

        # -- 日志
        log_card = tk.Frame(body, bg=C["log_bg"],
                            highlightbackground=C["border"],
                            highlightthickness=1, bd=0)
        log_card.pack(fill="x", pady=(10, 0))
        self.log = tk.Text(log_card, bg=C["log_bg"], fg=C["log_fg"],
                           font=("Menlo", 10), height=5,
                           relief="flat", bd=0, state="disabled",
                           wrap="word", padx=12, pady=10, cursor="arrow")
        self.log.pack(fill="x")

        # -- 按钮行
        btn_row = tk.Frame(self.root, bg=C["bg"])
        btn_row.pack(pady=(16, 24))

        self.dl_btn = PillButton(
            btn_row, "⬇  开始下载", self._start,
            bg=C["accent"], hover=C["accent_h"], fg="white",
            px=40, py=12, r=22)
        self.dl_btn.pack(side="left", padx=6)

        self.stop_btn = PillButton(
            btn_row, "✕  停止", self._stop,
            bg="#E5E5EA", hover="#D1D1D6", fg=C["text2"],
            px=28, py=12, r=22)
        self.stop_btn.pack(side="left", padx=6)
        self.stop_btn.disable()

        self.open_btn = PillButton(
            btn_row, "📂  打开文件夹", self._open,
            bg=C["surface"], hover=C["accent_l"], fg=C["text2"],
            px=22, py=12, r=22)
        self.open_btn.pack(side="left", padx=6)

    # ── 操作 ─────────────────────────────────────────────────
    def _choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.save_dir.get())
        if d:
            self.save_dir.set(d)

    def _open(self):
        subprocess.run(["open", self.save_dir.get()])

    def _log(self, msg):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _status(self, msg, pct=None):
        self.status_lbl.configure(text=msg)
        if pct is not None:
            self.pct_lbl.configure(text=f"{pct:.0f}%")
            self.progress["value"] = pct
        else:
            self.pct_lbl.configure(text="")

    def _start(self):
        url = self.url_box.get().strip()
        if not url:
            messagebox.showwarning("提示", "请先粘贴视频链接")
            return
        if self.downloading:
            return
        self.downloading = True
        self.progress["value"] = 0
        self._status("正在解析链接…")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.dl_btn.disable()
        self.stop_btn.enable()
        threading.Thread(target=self._thread, args=(url,), daemon=True).start()

    def _thread(self, url):
        out = os.path.join(self.save_dir.get(), "%(title)s.%(ext)s")
        try:
            cmd = find_ytdlp()
        except FileNotFoundError as e:
            self.root.after(0, self._status, str(e))
            self.root.after(0, self._reset)
            return

        cmd += [
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best",
            "--merge-output-format", "mp4",
            "--no-playlist", "--newline",
            "--no-check-certificates",
            "-o", out, url,
        ]
        try:
            self._proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace")
            for line in self._proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self.root.after(0, self._log, line)
                self.root.after(0, self._parse, line)
            self._proc.wait()
            rc = self._proc.returncode
            if rc == 0:
                self.root.after(0, self._status, "✅  下载完成！", 100)
                self.root.after(0, self._open)
            elif rc == -15:
                self.root.after(0, self._status, "已停止")
            else:
                self.root.after(0, self._status, "❌  下载失败，请检查链接或网络")
        except Exception as e:
            self.root.after(0, self._status, f"错误：{e}")
        finally:
            self._proc = None
            self.root.after(0, self._reset)

    def _parse(self, line):
        if "[download]" in line and "%" in line:
            try:
                pct   = float(line.split("%")[0].split()[-1])
                speed = line.split("|")[-1].strip() if "|" in line else ""
                self._status(f"下载中  {speed}", pct)
            except Exception:
                pass
        elif "[Merger]" in line or "Merging" in line:
            self._status("正在合并音视频…")
        elif "[ExtractAudio]" in line:
            self._status("正在提取音频…")
        elif "Downloading" in line and "[youtube]" in line:
            self._status("正在解析视频信息…")

    def _stop(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
        self._status("正在停止…")

    def _reset(self):
        self.downloading = False
        self.dl_btn.enable()
        self.stop_btn.disable()


def main():
    root = tk.Tk()
    root.tk.call("tk", "scaling", 2.0)
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
