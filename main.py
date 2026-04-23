#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
import sys
import os

BG = "#1a1a2e"
FG = "#e0e0e0"
ACCENT = "#e94560"
ENTRY_BG = "#16213e"
BTN_BG = "#e94560"
BTN_FG = "#ffffff"
FONT = ("Inter", 10)
FONT_BOLD = ("Inter", 10, "bold")

VIDEO_QUALITIES = ["best", "2160", "1440", "1080", "720", "480", "360"]
AUDIO_QUALITIES = ["best", "320", "192", "128", "96"]


def ensure_ytdlp():
    try:
        import yt_dlp
        return True
    except ImportError:
        return False


def install_ytdlp(log):
    log("Installing yt-dlp...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--user", "yt-dlp"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log("yt-dlp installed. Ready.")
        return True
    log(f"Install failed: {result.stderr.strip()}")
    return False


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YT Downloader")
        self.configure(bg=BG)
        self.resizable(False, False)
        self._build_ui()
        self.output_dir = os.path.expanduser("~/Downloads")

    def _build_ui(self):
        pad = {"padx": 16, "pady": 6}

        # Title
        tk.Label(self, text="YT Downloader", bg=BG, fg=ACCENT,
                 font=("Inter", 15, "bold")).pack(pady=(18, 4))

        # URL
        tk.Label(self, text="URL", bg=BG, fg=FG, font=FONT_BOLD, anchor="w").pack(fill="x", **pad)
        self.url_var = tk.StringVar()
        url_entry = tk.Entry(self, textvariable=self.url_var, bg=ENTRY_BG, fg=FG,
                             insertbackground=FG, relief="flat", font=FONT, width=52)
        url_entry.pack(fill="x", **pad)

        # Format row
        row = tk.Frame(self, bg=BG)
        row.pack(fill="x", **pad)

        tk.Label(row, text="Format", bg=BG, fg=FG, font=FONT_BOLD).pack(side="left")
        self.fmt_var = tk.StringVar(value="mp4")
        for fmt in ("mp4", "mp3"):
            tk.Radiobutton(row, text=fmt.upper(), variable=self.fmt_var, value=fmt,
                           bg=BG, fg=FG, selectcolor=ENTRY_BG, activebackground=BG,
                           font=FONT, command=self._on_format_change).pack(side="left", padx=8)

        tk.Label(row, text="  Quality", bg=BG, fg=FG, font=FONT_BOLD).pack(side="left")
        self.quality_var = tk.StringVar(value="best")
        self.quality_cb = ttk.Combobox(row, textvariable=self.quality_var,
                                       values=VIDEO_QUALITIES, width=8, state="readonly",
                                       font=FONT)
        self.quality_cb.pack(side="left", padx=8)
        self._style_combobox()

        # Output dir
        dir_row = tk.Frame(self, bg=BG)
        dir_row.pack(fill="x", **pad)
        tk.Label(dir_row, text="Save to", bg=BG, fg=FG, font=FONT_BOLD).pack(side="left")
        self.dir_label = tk.Label(dir_row, text=os.path.expanduser("~/Downloads"),
                                  bg=BG, fg="#888", font=FONT)
        self.dir_label.pack(side="left", padx=8)
        tk.Button(dir_row, text="Browse", bg=ENTRY_BG, fg=FG, relief="flat",
                  font=FONT, cursor="hand2", command=self._browse).pack(side="left")

        # Download button
        self.dl_btn = tk.Button(self, text="Download", bg=BTN_BG, fg=BTN_FG,
                                relief="flat", font=FONT_BOLD, cursor="hand2",
                                padx=24, pady=8, command=self._start_download)
        self.dl_btn.pack(pady=(10, 6))

        # Progress bar
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("red.Horizontal.TProgressbar",
                        troughcolor=ENTRY_BG, background=ACCENT, bordercolor=BG)
        self.progress = ttk.Progressbar(self, style="red.Horizontal.TProgressbar",
                                        length=460, mode="indeterminate")
        self.progress.pack(padx=16, pady=4)

        # Log
        self.log_text = tk.Text(self, bg=ENTRY_BG, fg="#aaa", font=("Monospace", 9),
                                height=8, relief="flat", state="disabled", wrap="word")
        self.log_text.pack(fill="x", padx=16, pady=(4, 16))

    def _style_combobox(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=ENTRY_BG, background=ENTRY_BG,
                        foreground=FG, selectbackground=ACCENT, arrowcolor=FG)

    def _on_format_change(self):
        if self.fmt_var.get() == "mp3":
            self.quality_cb.config(values=AUDIO_QUALITIES)
            self.quality_var.set("best")
        else:
            self.quality_cb.config(values=VIDEO_QUALITIES)
            self.quality_var.set("best")

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.output_dir)
        if d:
            self.output_dir = d
            self.dir_label.config(text=d)

    def _log(self, msg):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Paste a YouTube URL first.")
            return
        self.dl_btn.config(state="disabled")
        self.progress.start(12)
        threading.Thread(target=self._download, args=(url,), daemon=True).start()

    def _download(self, url):
        if not ensure_ytdlp():
            ok = install_ytdlp(lambda m: self.after(0, self._log, m))
            if not ok:
                self.after(0, self._finish, False)
                return

        import yt_dlp

        fmt = self.fmt_var.get()
        quality = self.quality_var.get()
        out = os.path.join(self.output_dir, "%(title)s.%(ext)s")

        ydl_opts = {
            "outtmpl": out,
            "progress_hooks": [self._ydl_hook],
            "quiet": True,
            "no_warnings": True,
        }

        if fmt == "mp3":
            ydl_opts["format"] = "bestaudio/best"
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality if quality != "best" else "0",
            }]
        else:
            if quality == "best":
                ydl_opts["format"] = "bestvideo+bestaudio/best"
            else:
                ydl_opts["format"] = (
                    f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"
                )
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }]
            ydl_opts["merge_output_format"] = "mp4"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                self.after(0, self._log, f"Fetching: {url}")
                ydl.download([url])
            self.after(0, self._log, "Done! File saved to " + self.output_dir)
            self.after(0, self._finish, True)
        except Exception as e:
            self.after(0, self._log, f"Error: {e}")
            self.after(0, self._finish, False)

    def _ydl_hook(self, d):
        if d["status"] == "downloading":
            pct = d.get("_percent_str", "").strip()
            speed = d.get("_speed_str", "").strip()
            eta = d.get("_eta_str", "").strip()
            if pct:
                self.after(0, self._log, f"  {pct}  speed: {speed}  eta: {eta}")
        elif d["status"] == "finished":
            self.after(0, self._log, "  Processing...")

    def _finish(self, success):
        self.progress.stop()
        self.dl_btn.config(state="normal")
        if success:
            self.progress.config(mode="determinate")
            self.progress["value"] = 100


if __name__ == "__main__":
    app = App()
    app.mainloop()
