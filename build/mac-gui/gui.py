#!/usr/bin/env python3
"""Antu Legal Search — Native GUI Launcher for macOS"""

import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# Resolve install directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_URL = "https://github.com/mlpfim0502/law-search-tool.git"
PORT = 8000


def run_cmd(cmd, cwd=None, capture=True):
    """Run a shell command and return (returncode, stdout, stderr)."""
    if cwd is None:
        cwd = APP_DIR
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=capture,
            text=True,
            timeout=300,
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


class AntuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Antu Legal Search")
        self.root.geometry("560x420")
        self.root.minsize(480, 360)
        self.root.configure(bg="#f5f5f7")

        # Apple-style fonts
        self.font_title = ("SF Pro Display", 18, "bold")
        self.font_body = ("SF Pro Text", 13)
        self.font_small = ("SF Pro Text", 11)
        self.font_mono = ("SF Mono", 11)

        self.setup_ui()
        self.check_docker()

    def setup_ui(self):
        # Title
        title = tk.Label(
            self.root,
            text="Antu Legal Search",
            font=self.font_title,
            bg="#f5f5f7",
            fg="#1d1d1f",
        )
        title.pack(pady=(20, 4))

        subtitle = tk.Label(
            self.root,
            text="輕量級法律搜尋系統",
            font=self.font_small,
            bg="#f5f5f7",
            fg="#86868b",
        )
        subtitle.pack(pady=(0, 16))

        # Button frame
        btn_frame = tk.Frame(self.root, bg="#f5f5f7")
        btn_frame.pack(pady=8)

        self.btn_start = self.make_button(btn_frame, "啟動服務", self.on_start, "#0071e3")
        self.btn_stop = self.make_button(btn_frame, "停止服務", self.on_stop, "#ff3b30")
        self.btn_browser = self.make_button(btn_frame, "開啟瀏覽器", self.on_browser, "#34c759")
        self.btn_update = self.make_button(btn_frame, "檢查更新", self.on_update, "#ff9f0a")

        # Status bar
        self.status_var = tk.StringVar(value="就緒")
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=self.font_small,
            bg="#f5f5f7",
            fg="#86868b",
            anchor="w",
        )
        self.status_bar.pack(fill="x", padx=20, pady=(8, 0))

        # Log area
        self.log_area = scrolledtext.ScrolledText(
            self.root,
            font=self.font_mono,
            bg="#ffffff",
            fg="#1d1d1f",
            wrap="word",
            state="disabled",
            height=10,
            borderwidth=1,
            relief="solid",
            highlightthickness=0,
        )
        self.log_area.pack(fill="both", expand=True, padx=20, pady=(8, 20))

    def make_button(self, parent, text, command, color):
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.font_body,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            cursor="hand2",
            borderwidth=0,
            highlightthickness=0,
            padx=16,
            pady=8,
            width=10,
        )
        btn.pack(side="left", padx=4)
        return btn

    def log(self, text):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", text + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    def check_docker(self):
        rc, out, err = run_cmd("docker info", capture=True)
        if rc != 0:
            self.log("⚠️ Docker 未啟動或尚未安裝")
            self.log("請先安裝 Docker Desktop 並確認左下角顯示綠燈")
            self.set_status("需要安裝 Docker")
            messagebox.showwarning(
                "需要 Docker",
                "請先安裝 Docker Desktop 並啟動。\n\n下載：https://www.docker.com/products/docker-desktop",
            )
        else:
            self.log("✓ Docker 已就緒")
            self.set_status("Docker 已就緒")

    def on_start(self):
        def task():
            self.set_status("正在啟動...")
            self.log("--- 啟動服務 ---")

            # Ensure directory exists
            if not os.path.isdir(APP_DIR):
                self.log("首次安裝，正在下載...")
                rc, out, err = run_cmd(f"git clone --depth 1 {REPO_URL} '{APP_DIR}'", cwd=os.path.expanduser("~"))
                if rc != 0:
                    self.log(f"下載失敗: {err}")
                    self.set_status("下載失敗")
                    return

            # Create dirs
            for d in ["data", "uploads"]:
                os.makedirs(os.path.join(APP_DIR, d), exist_ok=True)

            # Start
            rc, out, err = run_cmd("docker-compose up --build -d", cwd=APP_DIR)
            if rc != 0:
                self.log(f"啟動失敗: {err}")
                self.set_status("啟動失敗")
                return

            self.log("✓ 服務已啟動")
            self.log(f"請開啟瀏覽器訪問 http://localhost:{PORT}")
            self.set_status(f"運行中 — http://localhost:{PORT}")

        threading.Thread(target=task, daemon=True).start()

    def on_stop(self):
        def task():
            self.set_status("正在停止...")
            self.log("--- 停止服務 ---")
            rc, out, err = run_cmd("docker-compose down", cwd=APP_DIR)
            if rc != 0:
                self.log(f"停止失敗: {err}")
                self.set_status("停止失敗")
                return
            self.log("✓ 服務已停止")
            self.set_status("已停止")
        threading.Thread(target=task, daemon=True).start()

    def on_browser(self):
        self.log("開啟瀏覽器...")
        run_cmd(f"open http://localhost:{PORT}")

    def on_update(self):
        def task():
            self.set_status("檢查更新中...")
            self.log("--- 檢查更新 ---")

            if not os.path.isdir(os.path.join(APP_DIR, ".git")):
                self.log("尚未安裝，無法更新")
                self.set_status("尚未安裝")
                return

            rc, out, err = run_cmd("git fetch origin main", cwd=APP_DIR)
            if rc != 0:
                self.log(f"檢查失敗: {err}")
                self.set_status("檢查失敗")
                return

            rc_local, local, _ = run_cmd("git rev-parse HEAD", cwd=APP_DIR)
            rc_remote, remote, _ = run_cmd("git rev-parse origin/main", cwd=APP_DIR)

            if local.strip() == remote.strip():
                self.log("✓ 已經是最新版本")
                self.set_status("已是最新版")
                return

            self.log("發現新版本，正在更新...")
            rc, out, err = run_cmd("git pull origin main", cwd=APP_DIR)
            if rc != 0:
                self.log(f"更新失敗: {err}")
                self.set_status("更新失敗")
                return

            self.log("重建並重啟...")
            rc, out, err = run_cmd("docker-compose down && docker-compose up --build -d", cwd=APP_DIR)
            if rc != 0:
                self.log(f"重啟失敗: {err}")
                self.set_status("重啟失敗")
                return

            self.log("✓ 更新完成")
            self.set_status("更新完成 — 運行中")

        threading.Thread(target=task, daemon=True).start()


def main():
    root = tk.Tk()
    app = AntuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
