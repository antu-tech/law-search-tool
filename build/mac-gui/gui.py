#!/usr/bin/env python3
"""Antu Legal Search — Native GUI Launcher for macOS"""

import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

APP_DIR = os.path.expanduser("~/antu-legal-search")
REPO_URL = "https://github.com/antu-tech/law-search-tool.git"
PORT = 8000
DOCKER_DOWNLOAD_URL = "https://www.docker.com/products/docker-desktop"


def run_cmd(cmd, cwd=None, capture=True):
    if cwd is None:
        cwd = APP_DIR
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=capture,
            text=True, timeout=300,
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except Exception as e:
        return -1, "", str(e)


class AntuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Antu Legal Search")
        self.root.geometry("600x520")
        self.root.minsize(520, 400)
        self.root.configure(bg="#f5f5f7")

        self.font_title = ("SF Pro Display", 18, "bold")
        self.font_body = ("SF Pro Text", 13)
        self.font_small = ("SF Pro Text", 11)
        self.font_mono = ("SF Mono", 11)

        self.docker_ready = False
        self.polling = False

        self.setup_ui()
        self.check_docker_silent()

    def setup_ui(self):
        # Title
        tk.Label(self.root, text="Antu Legal Search",
                 font=self.font_title, bg="#f5f5f7", fg="#1d1d1f").pack(pady=(20, 4))
        tk.Label(self.root, text="輕量級法律搜尋系統",
                 font=self.font_small, bg="#f5f5f7", fg="#86868b").pack(pady=(0, 12))

        # --- Docker Status Panel ---
        self.docker_panel = tk.Frame(self.root, bg="#f5f5f7")
        self.docker_panel.pack(fill="x", padx=24, pady=(0, 8))

        self.docker_indicator = tk.Canvas(self.docker_panel, width=12, height=12,
                                          bg="#f5f5f7", highlightthickness=0)
        self.docker_indicator.pack(side="left", padx=(0, 8))
        self.docker_circle = self.docker_indicator.create_oval(2, 2, 10, 10, fill="#ff3b30")

        self.docker_label = tk.Label(self.docker_panel, text="檢查 Docker 狀態...",
                                     font=self.font_body, bg="#f5f5f7", fg="#1d1d1f")
        self.docker_label.pack(side="left")

        # --- Main Action Buttons ---
        self.btn_frame = tk.Frame(self.root, bg="#f5f5f7")
        self.btn_frame.pack(pady=8)

        self.btn_start = self.make_button(self.btn_frame, "啟動服務", self.on_start, "#0071e3")
        self.btn_stop = self.make_button(self.btn_frame, "停止服務", self.on_stop, "#ff3b30")
        self.btn_browser = self.make_button(self.btn_frame, "開啟瀏覽器", self.on_browser, "#34c759")
        self.btn_update = self.make_button(self.btn_frame, "檢查更新", self.on_update, "#ff9f0a")

        self.set_buttons_enabled(False)

        # --- Setup Wizard (hidden by default) ---
        self.wizard_frame = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid")
        self.wizard_frame.pack(fill="x", padx=24, pady=8)
        self.wizard_frame.pack_forget()

        self.wizard_title = tk.Label(self.wizard_frame, text="", font=("SF Pro Text", 14, "bold"),
                                     bg="#ffffff", fg="#1d1d1f")
        self.wizard_title.pack(pady=(16, 8), padx=16)

        self.wizard_desc = tk.Label(self.wizard_frame, text="", font=self.font_small,
                                    bg="#ffffff", fg="#86868b", justify="left",
                                    wraplength=500)
        self.wizard_desc.pack(pady=(0, 12), padx=16)

        self.wizard_btn_frame = tk.Frame(self.wizard_frame, bg="#ffffff")
        self.wizard_btn_frame.pack(pady=(0, 16), padx=16)

        self.wizard_btn = tk.Button(self.wizard_btn_frame, text="", font=self.font_body,
                                    cursor="hand2", borderwidth=0, highlightthickness=0,
                                    padx=20, pady=8)
        self.wizard_btn.pack(side="left", padx=4)

        self.wizard_btn2 = tk.Button(self.wizard_btn_frame, text="", font=self.font_body,
                                     cursor="hand2", borderwidth=0, highlightthickness=0,
                                     padx=20, pady=8)
        self.wizard_btn2.pack(side="left", padx=4)

        # --- Log Area ---
        self.status_var = tk.StringVar(value="就緒")
        tk.Label(self.root, textvariable=self.status_var, font=self.font_small,
                 bg="#f5f5f7", fg="#86868b", anchor="w").pack(fill="x", padx=24, pady=(8, 0))

        self.log_area = scrolledtext.ScrolledText(
            self.root, font=self.font_mono, bg="#ffffff", fg="#1d1d1f",
            wrap="word", state="disabled", height=10,
            borderwidth=1, relief="solid", highlightthickness=0,
        )
        self.log_area.pack(fill="both", expand=True, padx=24, pady=(8, 20))

    def make_button(self, parent, text, command, color):
        btn = tk.Button(parent, text=text, command=command,
                        font=self.font_body, bg=color, fg="white",
                        activebackground=color, activeforeground="white",
                        cursor="hand2", borderwidth=0, highlightthickness=0,
                        padx=16, pady=8, width=10)
        btn.pack(side="left", padx=4)
        return btn

    # -- Thread-safe UI helpers (all tkinter calls run on main thread) --
    def log(self, text):
        def _do():
            self.log_area.configure(state="normal")
            self.log_area.insert("end", text + "\n")
            self.log_area.see("end")
            self.log_area.configure(state="disabled")
        self.root.after(0, _do)

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    def set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        self.root.after(0, lambda: [
            btn.configure(state=state)
            for btn in [self.btn_start, self.btn_stop, self.btn_browser, self.btn_update]
        ])

    def set_docker_status(self, ready, message):
        def _do():
            self.docker_ready = ready
            color = "#34c759" if ready else "#ff3b30"
            self.docker_indicator.itemconfig(self.docker_circle, fill=color)
            self.docker_label.config(text=message)
        self.root.after(0, _do)

    def show_docker_wizard(self):
        def _do():
            self.wizard_frame.pack(fill="x", padx=24, pady=8)
            self.wizard_title.config(text="第一步：安裝 Docker Desktop")
            self.wizard_desc.config(
                text="Antu Legal Search 需要 Docker Desktop 來運行後端服務。\n"
                     "1. 點選下方「下載 Docker」按鈕\n"
                     "2. 雙擊下載的 .dmg 並拖曳 Docker 到 Applications\n"
                     "3. 開啟 Docker Desktop，等待左下角變成綠色\n"
                     "4. 回到此視窗，點選「已完成安裝」"
            )
            self.wizard_btn.config(text="下載 Docker", bg="#0071e3", fg="white",
                                   activebackground="#0071e3", command=self.download_docker)
            self.wizard_btn2.config(text="已完成安裝", bg="#34c759", fg="white",
                                    activebackground="#34c759", command=self.on_docker_installed)
        self.root.after(0, _do)

    def check_docker_silent(self):
        def task():
            rc, out, err = run_cmd("docker info", capture=True)
            if rc == 0:
                self.set_docker_status(True, "Docker 已就緒")
                self.log("[OK] Docker 已就緒")
                self.set_buttons_enabled(True)
            else:
                self.set_docker_status(False, "需要安裝 Docker")
                self.log("[WARN] Docker 未安裝或未啟動")
                self.show_docker_wizard()
        threading.Thread(target=task, daemon=True).start()

    def download_docker(self):
        self.log("正在開啟 Docker Desktop 下載頁面...")
        run_cmd(f"open '{DOCKER_DOWNLOAD_URL}'")

    def on_docker_installed(self):
        self.root.after(0, lambda: self.wizard_desc.config(text="正在檢查 Docker 狀態，請稍候..."))
        self.root.after(0, lambda: self.wizard_btn.pack_forget())
        self.root.after(0, lambda: self.wizard_btn2.pack_forget())

        def poll():
            for i in range(60):  # Poll for up to 60 seconds
                rc, _, _ = run_cmd("docker info", capture=True)
                if rc == 0:
                    self.root.after(0, self.on_docker_ready)
                    return
                msg = f"等待 Docker 啟動中... ({i+1}s)"
                self.root.after(0, lambda m=msg: self.wizard_desc.config(text=m))
                time.sleep(1)
            self.root.after(0, self.on_docker_timeout)
        threading.Thread(target=poll, daemon=True).start()

    def on_docker_ready(self):
        self.set_docker_status(True, "Docker 已就緒")
        self.log("[OK] Docker 已就緒")
        self.root.after(0, lambda: self.wizard_frame.pack_forget())
        self.set_buttons_enabled(True)
        self.set_status("就緒 — 可以啟動服務")

    def on_docker_timeout(self):
        self.root.after(0, lambda: self.wizard_desc.config(
            text="未檢測到 Docker。請確認 Docker Desktop 已開啟且左下角為綠色。"
        ))
        self.root.after(0, lambda: self.wizard_btn.pack(side="left", padx=4))
        self.root.after(0, lambda: self.wizard_btn2.pack(side="left", padx=4))

    def on_start(self):
        if not self.docker_ready:
            messagebox.showwarning("需要 Docker", "請先完成 Docker 安裝")
            return

        def task():
            self.set_status("正在啟動...")
            self.log("--- 啟動服務 ---")

            if not os.path.isdir(APP_DIR):
                self.log("首次安裝，正在下載...")
                rc, _, err = run_cmd(f"git clone --depth 1 {REPO_URL} '{APP_DIR}'", cwd=os.path.expanduser("~"))
                if rc != 0:
                    self.log(f"[ERR] 下載失敗: {err}")
                    self.set_status("下載失敗")
                    return

            for d in ["data", "uploads"]:
                os.makedirs(os.path.join(APP_DIR, d), exist_ok=True)

            rc, _, err = run_cmd("docker-compose up --build -d", cwd=APP_DIR)
            if rc != 0:
                self.log(f"[ERR] 啟動失敗: {err}")
                self.set_status("啟動失敗")
                return

            self.log("[OK] 服務已啟動")
            self.log(f"請開啟瀏覽器訪問 http://localhost:{PORT}")
            self.set_status(f"運行中 — http://localhost:{PORT}")
        threading.Thread(target=task, daemon=True).start()

    def on_stop(self):
        def task():
            self.set_status("正在停止...")
            self.log("--- 停止服務 ---")
            rc, _, err = run_cmd("docker-compose down", cwd=APP_DIR)
            if rc != 0:
                self.log(f"[ERR] 停止失敗: {err}")
                self.set_status("停止失敗")
                return
            self.log("[OK] 服務已停止")
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
                self.log("[WARN] 尚未安裝，無法更新")
                self.set_status("尚未安裝")
                return

            rc, _, err = run_cmd("git fetch origin main", cwd=APP_DIR)
            if rc != 0:
                self.log(f"[ERR] 檢查失敗: {err}")
                self.set_status("檢查失敗")
                return

            _, local, _ = run_cmd("git rev-parse HEAD", cwd=APP_DIR)
            _, remote, _ = run_cmd("git rev-parse origin/main", cwd=APP_DIR)

            if local.strip() == remote.strip():
                self.log("[OK] 已經是最新版本")
                self.set_status("已是最新版")
                return

            self.log("發現新版本，正在更新...")
            rc, _, err = run_cmd("git pull origin main", cwd=APP_DIR)
            if rc != 0:
                self.log(f"[ERR] 更新失敗: {err}")
                self.set_status("更新失敗")
                return

            self.log("重建並重啟...")
            rc, _, err = run_cmd("docker-compose down && docker-compose up --build -d", cwd=APP_DIR)
            if rc != 0:
                self.log(f"[ERR] 重啟失敗: {err}")
                self.set_status("重啟失敗")
                return

            self.log("[OK] 更新完成")
            self.set_status("更新完成 — 運行中")
        threading.Thread(target=task, daemon=True).start()


def main():
    root = tk.Tk()
    app = AntuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
