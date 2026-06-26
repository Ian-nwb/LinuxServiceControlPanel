#!/usr/bin/env python3
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import time

SERVICES = [
    ("MySQL",      "mysql",        "🐬"),
    ("PostgreSQL", "postgresql",   "🐘"),
    ("MongoDB",    "mongod",       "🍃"),
    ("Redis",      "redis-server", "🔴"),
    ("Docker",     "docker",       "🐳"),
    ("Nginx",      "nginx",        "⚡"),
]

# ── Tokyo Night palette ───────────────────────────────────────────────────────
BG       = "#1a1b2e"
BG2      = "#16213e"
BG3      = "#0f3460"
PANEL    = "#1e2030"
BORDER   = "#2a2b3d"
FG       = "#c0caf5"
FG2      = "#a9b1d6"
MUTED    = "#565f89"
RUNNING  = "#9ece6a"
STOPPED  = "#f7768e"
WORKING  = "#e0af68"
DISABLED = "#414868"
ACCENT   = "#7aa2f7"
PURPLE   = "#bb9af7"
CYAN     = "#7dcfff"

FONT_MONO  = ("JetBrains Mono", 9)
FONT_LABEL = ("Sans", 10)
FONT_TITLE = ("Sans", 13, "bold")
FONT_SMALL = ("Mono", 8)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def is_installed(svc):
    r = run(["systemctl", "list-unit-files", f"{svc}.service"])
    return svc in r.stdout


def is_active(svc):
    r = run(["systemctl", "is-active", svc])
    return r.stdout.strip() == "active"


def is_enabled(svc):
    r = run(["systemctl", "is-enabled", svc])
    return r.stdout.strip() == "enabled"


def get_uptime(svc):
    r = run(["systemctl", "show", svc, "--property=ActiveEnterTimestamp"])
    line = r.stdout.strip()
    if "=" not in line:
        return ""
    ts_str = line.split("=", 1)[1].strip()
    if not ts_str:
        return ""
    try:
        from datetime import datetime
        fmt = "%a %Y-%m-%d %H:%M:%S %Z"
        ts = datetime.strptime(ts_str, fmt)
        delta = datetime.now() - ts
        s = int(delta.total_seconds())
        if s < 60:
            return f"{s}s"
        elif s < 3600:
            return f"{s//60}m"
        else:
            return f"{s//3600}h {(s%3600)//60}m"
    except Exception:
        return ""


def get_journal(svc, lines=40):
    r = run(["journalctl", "-u", svc, "-n", str(lines), "--no-pager", "--output=short-iso"])
    return r.stdout or "(no logs)"


# ── Pulsing dot canvas widget ─────────────────────────────────────────────────
class PulseDot(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, width=14, height=14, bg=BG, highlightthickness=0, **kw)
        self._color = MUTED
        self._alpha = 1.0
        self._dir = -1
        self._pulsing = False
        self._dot = self.create_oval(2, 2, 12, 12, fill=self._color, outline="")
        self._tick()

    def set_color(self, color, pulse=False):
        self._color = color
        self._pulsing = pulse
        if not pulse:
            self._alpha = 1.0
        self.itemconfig(self._dot, fill=color)

    def _tick(self):
        if self._pulsing:
            self._alpha += self._dir * 0.06
            if self._alpha <= 0.3:
                self._dir = 1
            elif self._alpha >= 1.0:
                self._dir = -1
            r, g, b = self.winfo_rgb(self._color)
            r = int((r / 65535) * self._alpha * 255)
            g = int((g / 65535) * self._alpha * 255)
            b = int((b / 65535) * self._alpha * 255)
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            self.itemconfig(self._dot, fill=hex_color)
        self.after(60, self._tick)


# ── Log window ────────────────────────────────────────────────────────────────
class LogWindow(tk.Toplevel):
    def __init__(self, parent, svc, label):
        super().__init__(parent)
        self.title(f"Logs — {label}")
        self.configure(bg=BG)
        self.geometry("780x420")
        self.svc = svc

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top, text=f"⚙  {label}", font=FONT_TITLE, fg=ACCENT, bg=BG).pack(side="left")
        ttk.Button(top, text="↻ refresh", command=self._load).pack(side="right")

        self.txt = scrolledtext.ScrolledText(
            self, font=("Mono", 8), bg=BG2, fg=FG2,
            insertbackground=FG, relief="flat", padx=8, pady=6,
            wrap="none"
        )
        self.txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.txt.tag_config("err",  foreground=STOPPED)
        self.txt.tag_config("warn", foreground=WORKING)
        self.txt.tag_config("ok",   foreground=RUNNING)
        self._load()

    def _load(self):
        logs = get_journal(self.svc)
        self.txt.config(state="normal")
        self.txt.delete("1.0", "end")
        for line in logs.splitlines():
            tag = ""
            low = line.lower()
            if any(w in low for w in ("error", "failed", "fatal", "crit")):
                tag = "err"
            elif any(w in low for w in ("warn", "notice")):
                tag = "warn"
            elif any(w in low for w in ("start", "ready", "success", "listening")):
                tag = "ok"
            self.txt.insert("end", line + "\n", tag)
        self.txt.config(state="disabled")
        self.txt.see("end")


# ── Service row ───────────────────────────────────────────────────────────────
class Row:
    def __init__(self, parent, row, label, svc, icon, log_cb):
        self.svc   = svc
        self.label = label
        self._log_cb = log_cb
        self._installed = True

        # dot
        self.dot = PulseDot(parent)
        self.dot.grid(row=row, column=0, padx=(8, 4), pady=8)

        # name
        tk.Label(parent, text=f"{icon}  {label}", font=FONT_LABEL,
                 fg=FG, bg=PANEL, anchor="w", width=13)\
            .grid(row=row, column=1, sticky="w")

        # status text
        self.status_var = tk.StringVar(value="checking…")
        self.status_lbl = tk.Label(parent, textvariable=self.status_var,
                                   font=("Mono", 9, "bold"), fg=MUTED,
                                   bg=PANEL, anchor="w", width=13)
        self.status_lbl.grid(row=row, column=2, sticky="w", padx=4)

        # uptime
        self.uptime_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.uptime_var,
                 font=FONT_SMALL, fg=MUTED, bg=PANEL, anchor="w", width=8)\
            .grid(row=row, column=3, sticky="w")

        # enabled toggle
        self.enabled_var = tk.StringVar(value="—")
        self.enabled_lbl = tk.Label(parent, textvariable=self.enabled_var,
                                    font=FONT_SMALL, fg=MUTED, bg=PANEL, width=8, anchor="w")
        self.enabled_lbl.grid(row=row, column=4, sticky="w")

        # buttons
        btn_cfg = dict(width=7)
        self.start_btn   = self._btn(parent, "▶ start",   lambda: self.act("start"),   **btn_cfg)
        self.stop_btn    = self._btn(parent, "■ stop",    lambda: self.act("stop"),    **btn_cfg)
        self.restart_btn = self._btn(parent, "↺ restart", lambda: self.act("restart"), **btn_cfg)
        self.log_btn     = self._btn(parent, "📋 logs",   lambda: self._log_cb(svc, label), width=7)

        self.start_btn.grid(row=row,   column=5, padx=2)
        self.stop_btn.grid(row=row,    column=6, padx=2)
        self.restart_btn.grid(row=row, column=7, padx=2)
        self.log_btn.grid(row=row,     column=8, padx=(2, 8))

    def _btn(self, parent, text, cmd, **kw):
        b = tk.Button(parent, text=text, command=cmd,
                      bg=BG3, fg=FG2, activebackground=ACCENT,
                      activeforeground=BG, relief="flat", bd=0,
                      padx=6, pady=3, font=("Sans", 9), cursor="hand2", **kw)
        return b

    def act(self, action):
        self.status_var.set("working…")
        self.status_lbl.config(fg=WORKING)
        self.dot.set_color(WORKING, pulse=True)
        self._set_buttons(False)
        threading.Thread(target=self._run_action, args=(action,), daemon=True).start()

    def _run_action(self, action):
        subprocess.run(["pkexec", "systemctl", action, self.svc])
        time.sleep(0.6)
        self.refresh()
        self._set_buttons(True)

    def _set_buttons(self, enabled):
        state = "normal" if enabled else "disabled"
        for b in (self.start_btn, self.stop_btn, self.restart_btn, self.log_btn):
            b.config(state=state)

    def refresh(self):
        if not is_installed(self.svc):
            self._installed = False
            self.status_var.set("not installed")
            self.status_lbl.config(fg=DISABLED)
            self.dot.set_color(DISABLED, pulse=False)
            self.uptime_var.set("")
            self.enabled_var.set("—")
            self._set_buttons(False)
            return
        self._installed = True
        active = is_active(self.svc)
        enabled = is_enabled(self.svc)
        if active:
            self.status_var.set("● running")
            self.status_lbl.config(fg=RUNNING)
            self.dot.set_color(RUNNING, pulse=True)
            self.uptime_var.set(get_uptime(self.svc))
        else:
            self.status_var.set("○ stopped")
            self.status_lbl.config(fg=STOPPED)
            self.dot.set_color(STOPPED, pulse=False)
            self.uptime_var.set("")
        self.enabled_var.set("auto-start" if enabled else "manual")
        self.enabled_lbl.config(fg=CYAN if enabled else MUTED)
        self._set_buttons(True)


# ── Main App ──────────────────────────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        root.title("DB Control Panel")
        root.configure(bg=BG)
        root.geometry("780x420")
        root.resizable(True, True)

        # ── header
        hdr = tk.Frame(root, bg=BG2, pady=10)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  Service Control Panel",
                 font=FONT_TITLE, fg=ACCENT, bg=BG2).pack(side="left", padx=16)
        self.clock_lbl = tk.Label(hdr, text="", font=FONT_SMALL, fg=MUTED, bg=BG2)
        self.clock_lbl.pack(side="right", padx=16)
        self._tick_clock()

        # ── column headers
        hrow = tk.Frame(root, bg=PANEL)
        hrow.pack(fill="x", padx=0)
        for col, (text, w) in enumerate([
            ("", 2), ("service", 13), ("status", 13), ("uptime", 8),
            ("boot", 8), ("", 7), ("", 7), ("", 7), ("", 7)
        ]):
            tk.Label(hrow, text=text.upper(), font=("Sans", 7), fg=MUTED,
                     bg=PANEL, width=w, anchor="w")\
                .grid(row=0, column=col, padx=(8 if col == 0 else 2), pady=4, sticky="w")

        # ── separator
        tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

        # ── rows
        self.frame = tk.Frame(root, bg=PANEL)
        self.frame.pack(fill="both", expand=True)
        self.rows = [
            Row(self.frame, i, label, svc, icon, self._open_logs)
            for i, (label, svc, icon) in enumerate(SERVICES)
        ]

        # ── footer
        foot = tk.Frame(root, bg=BG2, pady=6)
        foot.pack(fill="x", side="bottom")
        self.summary_lbl = tk.Label(foot, text="", font=FONT_SMALL, fg=MUTED, bg=BG2)
        self.summary_lbl.pack(side="left", padx=16)
        tk.Button(foot, text="↻  Refresh All", command=self.refresh_all,
                  bg=BG3, fg=FG2, activebackground=ACCENT, activeforeground=BG,
                  relief="flat", bd=0, padx=10, pady=4, font=("Sans", 9), cursor="hand2")\
            .pack(side="right", padx=12)

        self._auto_refresh()

    def _open_logs(self, svc, label):
        LogWindow(self.root, svc, label)

    def refresh_all(self):
        for r in self.rows:
            threading.Thread(target=r.refresh, daemon=True).start()
        self.root.after(800, self._update_summary)

    def _update_summary(self):
        running = sum(1 for r in self.rows if r._installed and is_active(r.svc))
        total   = sum(1 for r in self.rows if r._installed)
        self.summary_lbl.config(
            text=f"{running}/{total} services running  •  last refreshed {time.strftime('%H:%M:%S')}"
        )

    def _auto_refresh(self):
        self.refresh_all()
        self.root.after(8000, self._auto_refresh)

    def _tick_clock(self):
        self.clock_lbl.config(text=time.strftime("  %A %d %b  %H:%M:%S  "))
        self.root.after(1000, self._tick_clock)


if __name__ == "__main__":
    root = tk.Tk()

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TButton",
        background=BG3, foreground=FG2, borderwidth=0,
        focusthickness=0, focuscolor="none", padding=4)
    style.map("TButton", background=[("active", ACCENT)], foreground=[("active", BG)])

    App(root)
    root.mainloop()
