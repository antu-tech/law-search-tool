#!/usr/bin/env python3
"""Antu Legal Search — Native GUI Launcher for macOS"""

import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext
import queue

APP_DIR = os.path.expanduser("~/antu-legal-search")
REPO_URL = "https://github.com/antu-tech/law-search-tool.git"
PORT = 8000
DOCKER_DOWNLOAD_URL = "https://www.docker.com/products/docker-desktop"

# ── App Design Tokens (match law-search-tool Apple Design Language) ──
COLORS = {
    "bg": "#f5f5f7",
    "surface": "#ffffff",
    "primary": "#0071e3",
    "primary_hover": "#0077ed",
    "danger": "#ff3b30",
    "success": "#34c759",
    "warning": "#ff9f0a",
    "text": "#1d1d1f",
    "text_secondary": "#86868b",
    "text_tertiary": "#a1a1a6",
    "border": "#d2d2d7",
    "border_subtle": "#e8e8ed",
}


def _resolve_font(name, size, weight="normal"):
    """Try SF Pro, fallback to system fonts."""
    families = {
        "display": ["SF Pro Display", "Helvetica Neue", "Arial", "TkDefaultFont"],
        "text": ["SF Pro Text", "Helvetica Neue", "Arial", "TkDefaultFont"],
        "mono": ["SF Mono", "Menlo", "Consolas", "Courier", "TkFixedFont"],
    }
    for family in families.get(name, ["TkDefaultFont"]):
        try:
            tk.Frame().destroy()  # ensure tk is initialized
            return (family, size, weight)
        except Exception:
            continue
    return ("TkDefaultFont", size, weight)


def _docker_path():
    """Find docker executable across common macOS install locations."""
    path = shutil.which("docker")
    if path:
        return path
    for candidate in (
        "/usr/local/bin/docker",
        "/opt/homebrew/bin/docker",
        "/usr/bin/docker",
        os.path.expanduser("~/.docker/bin/docker"),
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "docker"


def _docker_compose_cmd():
    """Return working docker compose command as a list, or None."""
    docker = _docker_path()
    try:
        result = subprocess.run(
            [docker, "compose", "version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return [docker, "compose"]
    except Exception:
        pass
    compose = shutil.which("docker-compose")
    if compose:
        return [compose]
    for candidate in (
        "/usr/local/bin/docker-compose",
        "/opt/homebrew/bin/docker-compose",
        "/usr/bin/docker-compose",
    ):
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return [candidate]
    return None


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
        self.root.geometry("640x560")
        self.root.minsize(560, 440)
        self.root.configure(bg=COLORS["bg"])

        self.font_title = _resolve_font("display", 20, "bold")
        self.font_body = _resolve_font("text", 13)
        self.font_small = _resolve_font("text", 12)
        self.font_caption = _resolve_font("text", 11)
        self.font_mono = _resolve_font("mono", 12)

        self.docker_ready = False
        self.polling = False

        # Thread-safe queue for UI updates from worker threads
        self.ui_queue = queue.Queue()
        self._poll_ui_queue()

        self.setup_ui()
        self.check_docker_silent()

    def _poll_ui_queue(self):
        """Process UI update callbacks on the main thread."""
        try:
            while True:
                func = self.ui_queue.get_nowait()
                try:
                    func()
                except Exception as e:
                    print(f"UI queue error: {e}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_ui_queue)

    def _ui(self, func):
        """Schedule a UI update from any thread."""
        self.ui_queue.put(func)

    # ── UI Building ──

    def setup_ui(self):
        # Header
        header = tk.Frame(self.root, bg=COLORS["bg"])
        header.pack(fill="x", padx=32, pady=(24, 4))
        tk.Label(header, text="Antu Legal Search",
                 font=self.font_title, bg=COLORS["bg"], fg=COLORS["text"]).pack(anchor="w")
        tk.Label(header, text="輕量級法律搜尋系統",
                 font=self.font_caption, bg=COLORS["bg"], fg=COLORS["text_secondary"]).pack(anchor="w")

        # Status bar (Docker)
        self.status_bar = tk.Frame(self.root, bg=COLORS["surface"],
                                   highlightbackground=COLORS["border_subtle"],
                                   highlightthickness=1)
        self.status_bar.pack(fill="x", padx=32, pady=(16, 0))
        self.status_bar_inner = tk.Frame(self.status_bar, bg=COLORS["surface"])
        self.status_bar_inner.pack(fill="x", padx=16, pady=12)

        self.docker_indicator = tk.Canvas(self.status_bar_inner, width=10, height=10,
                                          bg=COLORS["surface"], highlightthickness=0)
        self.docker_indicator.pack(side="left", padx=(0, 10))
        self.docker_circle = self.docker_indicator.create_oval(0, 0, 10, 10,
                                                                fill=COLORS["danger"],
                                                                outline="")
        self.docker_label = tk.Label(self.status_bar_inner, text="檢查 Docker 狀態...",
                                     font=self.font_small, bg=COLORS["surface"],
                                     fg=COLORS["text"])
        self.docker_label.pack(side="left")

        # Action buttons
        self.btn_frame = tk.Frame(self.root, bg=COLORS["bg"])
        self.btn_frame.pack(fill="x", padx=32, pady=(16, 0))

        self.btn_start = self._pill_button(self.btn_frame, "啟動服務",
                                           self.on_start, COLORS["primary"])
        self.btn_stop = self._pill_button(self.btn_frame, "停止服務",
                                          self.on_stop, COLORS["danger"])
        self.btn_browser = self._pill_button(self.btn_frame, "開啟瀏覽器",
                                             self.on_browser, COLORS["success"])
        self.btn_update = self._pill_button(self.btn_frame, "檢查更新",
                                            self.on_update, COLORS["warning"])

        self.set_buttons_enabled(False)

        # Wizard card (hidden by default)
        self.wizard_frame = tk.Frame(self.root, bg=COLORS["surface"],
                                     highlightbackground=COLORS["border_subtle"],
                                     highlightthickness=1)
        self.wizard_frame.pack(fill="x", padx=32, pady=(16, 0))
        self.wizard_frame.pack_forget()

        self.wizard_title = tk.Label(self.wizard_frame, text="",
                                     font=_resolve_font("text", 15, "bold"),
                                     bg=COLORS["surface"], fg=COLORS["text"])
        self.wizard_title.pack(anchor="w", padx=20, pady=(20, 8))

        self.wizard_desc = tk.Label(self.wizard_frame, text="",
                                    font=self.font_caption,
                                    bg=COLORS["surface"], fg=COLORS["text_secondary"],
                                    justify="left", wraplength=540)
        self.wizard_desc.pack(anchor="w", padx=20, pady=(0, 16))

        self.wizard_btn_frame = tk.Frame(self.wizard_frame, bg=COLORS["surface"])
        self.wizard_btn_frame.pack(anchor="w", padx=20, pady=(0, 20))

        self.wizard_btn = self._pill_button(self.wizard_btn_frame, "",
                                            None, COLORS["primary"])
        self.wizard_btn2 = self._pill_button(self.wizard_btn_frame, "",
                                             None, COLORS["success"])

        # Log header
        log_header = tk.Frame(self.root, bg=COLORS["bg"])
        log_header.pack(fill="x", padx=32, pady=(16, 0))
        self.status_var = tk.StringVar(value="就緒")
        tk.Label(log_header, textvariable=self.status_var,
                 font=self.font_caption, bg=COLORS["bg"],
                 fg=COLORS["text_secondary"]).pack(anchor="w")

        # Log area
        self.log_area = scrolledtext.ScrolledText(
            self.root, font=self.font_mono, bg=COLORS["surface"],
            fg=COLORS["text"], wrap="word", state="disabled", height=12,
            borderwidth=0, highlightthickness=1,
            highlightbackground=COLORS["border_subtle"],
            highlightcolor=COLORS["border_subtle"],
            padx=12, pady=12,
        )
        self.log_area.pack(fill="both", expand=True, padx=32, pady=(8, 24))

    def _pill_button(self, parent, text, command, color):
        """Build a flat, rounded-feeling button (pill-like within tkinter limits)."""
        btn = tk.Button(parent, text=text, command=command,
                        font=self.font_small, bg=color, fg="white",
                        activebackground=color, activeforeground="white",
                        cursor="hand2", borderwidth=0, highlightthickness=0,
                        padx=18, pady=7)
        btn.pack(side="left", padx=(0, 8))
        return btn

    # ── UI Helpers ──

    def log(self, text):
        self.log_area.configure(state="normal")
        self.log_area.insert("end", text + "\n")
        self.log_area.see("end")
        self.log_area.configure(state="disabled")

    def set_status(self, text):
        self.status_var.set(text)

    def set_buttons_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for btn in (self.btn_start, self.btn_stop, self.btn_browser, self.btn_update):
            btn.configure(state=state)

    def set_docker_status(self, ready, message):
        self.docker_ready = ready
        color = COLORS["success"] if ready else COLORS["danger"]
        self.docker_indicator.itemconfig(self.docker_circle, fill=color)
        self.docker_label.config(text=message)

    # ── Wizard / Docker ──

    def show_docker_wizard(self):
        self.wizard_frame.pack(fill="x", padx=32, pady=(16, 0))
        self.wizard_title.config(text="需要 Docker Desktop")
        self.wizard_desc.config(
            text="Antu Legal Search 需要 Docker Desktop 來運行後端服務。\n"
                 "1. 點選「下載 Docker」\n"
                 "2. 雙擊 .dmg 並拖曳 Docker 到 Applications\n"
                 "3. 開啟 Docker Desktop，等待左下角變綠\n"
                 "4. 回到此視窗，點選「已完成安裝」"
        )
        self.wizard_btn.config(text="下載 Docker", command=self.download_docker)
        self.wizard_btn2.config(text="已完成安裝", command=self.on_docker_installed)

    def check_docker_silent(self):
        def task():
            docker = _docker_path()
            rc, out, err = run_cmd(f'"{docker}" info', capture=True)
            if rc == 0:
                self._ui(lambda: self.set_docker_status(True, "Docker 已就緒"))
                self._ui(lambda: self.log("[OK] Docker 已就緒"))
                self._ui(lambda: self.set_buttons_enabled(True))
            else:
                self._ui(lambda: self.set_docker_status(False, "需要安裝 Docker"))
                if "Cannot connect" in err or "Is the docker daemon running" in err:
                    self._ui(lambda: self.log("[WARN] Docker 已安裝但未啟動，請開啟 Docker Desktop"))
                elif "command not found" in err or "No such file" in err:
                    self._ui(lambda: self.log("[WARN] 未檢測到 Docker，請安裝 Docker Desktop"))
                else:
                    self._ui(lambda: self.log(f"[WARN] Docker 檢查失敗: {err.strip() or out.strip()}"))
                self._ui(lambda: self.show_docker_wizard())
        threading.Thread(target=task, daemon=True).start()

    def download_docker(self):
        self.log("正在開啟 Docker Desktop 下載頁面...")
        run_cmd(f"open '{DOCKER_DOWNLOAD_URL}'")

    def on_docker_installed(self):
        self._ui(lambda: self.wizard_desc.config(text="正在檢查 Docker 狀態，請稍候..."))
        self._ui(lambda: self.wizard_btn.pack_forget())
        self._ui(lambda: self.wizard_btn2.pack_forget())

        def poll():
            docker = _docker_path()
            for i in range(60):
                rc, _, _ = run_cmd(f'"{docker}" info', capture=True)
                if rc == 0:
                    self._ui(self.on_docker_ready)
                    return
                msg = f"等待 Docker 啟動中... ({i+1}s)"
                self._ui(lambda m=msg: self.wizard_desc.config(text=m))
                time.sleep(1)
            self._ui(self.on_docker_timeout)
        threading.Thread(target=poll, daemon=True).start()

    def on_docker_ready(self):
        self.set_docker_status(True, "Docker 已就緒")
        self.log("[OK] Docker 已就緒")
        self.wizard_frame.pack_forget()
        self.set_buttons_enabled(True)
        self.set_status("就緒 — 可以啟動服務")

    def on_docker_timeout(self):
        self.wizard_desc.config(
            text="未檢測到 Docker。請確認 Docker Desktop 已開啟且左下角為綠色。"
        )
        self.wizard_btn.pack(side="left", padx=(0, 8))
        self.wizard_btn2.pack(side="left", padx=(0, 8))

    # ── Actions ──

    def on_start(self):
        if not self.docker_ready:
            messagebox.showwarning("需要 Docker", "請先完成 Docker 安裝")
            return

        def task():
            self._ui(lambda: self.set_status("正在啟動..."))
            self._ui(lambda: self.log("--- 啟動服務 ---"))

            if not os.path.isdir(APP_DIR):
                self._ui(lambda: self.log("首次安裝，正在下載..."))
                rc, _, err = run_cmd(f"git clone --depth 1 {REPO_URL} '{APP_DIR}'",
                                     cwd=os.path.expanduser("~"))
                if rc != 0:
                    self._ui(lambda: self.log(f"[ERR] 下載失敗: {err}"))
                    self._ui(lambda: self.set_status("下載失敗"))
                    return

            for d in ("data", "uploads"):
                os.makedirs(os.path.join(APP_DIR, d), exist_ok=True)

            compose = _docker_compose_cmd()
            if compose is None:
                self._ui(lambda: self.log("[ERR] 未找到 docker compose，請確認 Docker Desktop 已安裝"))
                self._ui(lambda: self.set_status("啟動失敗"))
                return
            compose_str = " ".join(f'"{c}"' for c in compose)
            rc, _, err = run_cmd(f"{compose_str} up --build -d", cwd=APP_DIR)
            if rc != 0:
                self._ui(lambda: self.log(f"[ERR] 啟動失敗: {err}"))
                self._ui(lambda: self.set_status("啟動失敗"))
                return

            self._ui(lambda: self.log("[OK] 服務已啟動"))
            self._ui(lambda: self.log(f"請開啟瀏覽器訪問 http://localhost:{PORT}"))
            self._ui(lambda: self.set_status(f"運行中 — http://localhost:{PORT}"))
        threading.Thread(target=task, daemon=True).start()

    def on_stop(self):
        def task():
            self._ui(lambda: self.set_status("正在停止..."))
            self._ui(lambda: self.log("--- 停止服務 ---"))
            compose = _docker_compose_cmd()
            if compose is None:
                self._ui(lambda: self.log("[ERR] 未找到 docker compose"))
                self._ui(lambda: self.set_status("停止失敗"))
                return
            compose_str = " ".join(f'"{c}"' for c in compose)
            rc, _, err = run_cmd(f"{compose_str} down", cwd=APP_DIR)
            if rc != 0:
                self._ui(lambda: self.log(f"[ERR] 停止失敗: {err}"))
                self._ui(lambda: self.set_status("停止失敗"))
                return
            self._ui(lambda: self.log("[OK] 服務已停止"))
            self._ui(lambda: self.set_status("已停止"))
        threading.Thread(target=task, daemon=True).start()

    def on_browser(self):
        self.log("開啟瀏覽器...")
        run_cmd(f"open http://localhost:{PORT}")

    def on_update(self):
        def task():
            self._ui(lambda: self.set_status("檢查更新中..."))
            self._ui(lambda: self.log("--- 檢查更新 ---"))

            if not os.path.isdir(os.path.join(APP_DIR, ".git")):
                self._ui(lambda: self.log("[WARN] 尚未安裝，無法更新"))
                self._ui(lambda: self.set_status("尚未安裝"))
                return

            rc, _, err = run_cmd("git fetch origin main", cwd=APP_DIR)
            if rc != 0:
                self._ui(lambda: self.log(f"[ERR] 檢查失敗: {err}"))
                self._ui(lambda: self.set_status("檢查失敗"))
                return

            _, local, _ = run_cmd("git rev-parse HEAD", cwd=APP_DIR)
            _, remote, _ = run_cmd("git rev-parse origin/main", cwd=APP_DIR)

            if local.strip() == remote.strip():
                self._ui(lambda: self.log("[OK] 已經是最新版本"))
                self._ui(lambda: self.set_status("已是最新版"))
                return

            self._ui(lambda: self.log("發現新版本，正在更新..."))
            rc, _, err = run_cmd("git pull origin main", cwd=APP_DIR)
            if rc != 0:
                self._ui(lambda: self.log(f"[ERR] 更新失敗: {err}"))
                self._ui(lambda: self.set_status("更新失敗"))
                return

            self._ui(lambda: self.log("重建並重啟..."))
            compose = _docker_compose_cmd()
            if compose is None:
                self._ui(lambda: self.log("[ERR] 未找到 docker compose"))
                self._ui(lambda: self.set_status("重啟失敗"))
                return
            compose_str = " ".join(f'"{c}"' for c in compose)
            rc, _, err = run_cmd(f"{compose_str} down && {compose_str} up --build -d", cwd=APP_DIR)
            if rc != 0:
                self._ui(lambda: self.log(f"[ERR] 重啟失敗: {err}"))
                self._ui(lambda: self.set_status("重啟失敗"))
                return

            self._ui(lambda: self.log("[OK] 更新完成"))
            self._ui(lambda: self.set_status("更新完成 — 運行中"))
        threading.Thread(target=task, daemon=True).start()


def main():
    root = tk.Tk()
    app = AntuApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
