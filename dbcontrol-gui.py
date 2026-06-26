#!/usr/bin/env python3
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext
import time
import socket
import re

# ── Service definitions ───────────────────────────────────────────────────────
# (label, systemd_service, icon, default_port)   port=None → no port check
SERVICES = [
    ("MySQL",      "mysql",        "🐬", 3306),
    ("PostgreSQL", "postgresql",   "🐘", 5432),
    ("MongoDB",    "mongod",       "🍃", 27017),
    ("Redis",      "redis-server", "🔴", 6379),
    ("Docker",     "docker",       "🐳", None),
    ("Nginx",      "nginx",        "⚡", 80),
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
WARN     = "#ff9e64"

FONT_LABEL = ("Sans", 10)
FONT_TITLE = ("Sans", 13, "bold")
FONT_SMALL = ("Mono", 8)
FONT_BOLD  = ("Mono", 9, "bold")


# ── Helpers ───────────────────────────────────────────────────────────────────
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

def toggle_enabled(svc, enable: bool):
    action = "enable" if enable else "disable"
    subprocess.run(["pkexec", "systemctl", action, svc])

def port_bound(port):
    """True if something is listening on localhost:port."""
    if port is None:
        return None
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except OSError:
        return False

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
        ts = datetime.strptime(ts_str, "%a %Y-%m-%d %H:%M:%S %Z")
        s = int((datetime.now() - ts).total_seconds())
        if s < 60:   return f"{s}s"
        if s < 3600: return f"{s//60}m"
        return f"{s//3600}h{(s%3600)//60}m"
    except Exception:
        return ""

def get_cpu_ram(svc):
    """Return (cpu_str, ram_str) from systemctl show."""
    r = run(["systemctl", "show", svc,
             "--property=CPUUsageNSec",
             "--property=MemoryCurrent"])
    cpu_str = ram_str = "—"
    for line in r.stdout.splitlines():
        if line.startswith("MemoryCurrent="):
            val = line.split("=", 1)[1].strip()
            try:
                b = int(val)
                if b > 0:
                    ram_str = f"{b/1024/1024:.1f}M" if b < 1073741824 else f"{b/1024/1024/1024:.1f}G"
            except ValueError:
                pass
        elif line.startswith("CPUUsageNSec="):
            val = line.split("=", 1)[1].strip()
            try:
                ns = int(val)
                if ns > 0:
                    cpu_str = f"{ns/1e9:.1f}s"
            except ValueError:
                pass
    return cpu_str, ram_str

def get_journal(svc, lines=60):
    r = run(["journalctl", "-u", svc, "-n", str(lines),
             "--no-pager", "--output=short-iso"])
    return r.stdout or "(no logs)"


# ── Pulsing dot ───────────────────────────────────────────────────────────────
class PulseDot(tk.Canvas):
    def __init__(self, parent, **kw):
        super().__init__(parent, width=14, height=14, bg=PANEL,
                         highlightthickness=0, **kw)
        self._color  = MUTED
        self._alpha  = 1.0
        self._dir    = -1
        self._pulsing = False
        self._dot = self.create_oval(2, 2, 12, 12, fill=self._color, outline="")
        self._tick()

    def set_color(self, color, pulse=False):
        self._color   = color
        self._pulsing = pulse
        if not pulse:
            self._alpha = 1.0
            self.itemconfig(self._dot, fill=color)

    def _tick(self):
        if self._pulsing:
            self._alpha += self._dir * 0.06
            if self._alpha <= 0.3: self._dir = 1
            elif self._alpha >= 1.0: self._dir = -1
            try:
                r, g, b = self.winfo_rgb(self._color)
                r = int((r/65535)*self._alpha*255)
                g = int((g/65535)*self._alpha*255)
                b = int((b/65535)*self._alpha*255)
                self.itemconfig(self._dot, fill=f"#{r:02x}{g:02x}{b:02x}")
            except Exception:
                pass
        self.after(60, self._tick)


# ── Log window ────────────────────────────────────────────────────────────────
class LogWindow(tk.Toplevel):
    def __init__(self, parent, svc, label):
        super().__init__(parent)
        self.title(f"Logs — {label}")
        self.configure(bg=BG)
        self.geometry("820x460")
        self.svc = svc

        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=10, pady=(10, 4))
        tk.Label(top, text=f"📋  {label} logs", font=FONT_TITLE,
                 fg=ACCENT, bg=BG).pack(side="left")
        tk.Button(top, text="↻ refresh", command=self._load,
                  bg=BG3, fg=FG2, activebackground=ACCENT, activeforeground=BG,
                  relief="flat", bd=0, padx=8, pady=3,
                  font=("Sans", 9), cursor="hand2").pack(side="right")

        self.txt = scrolledtext.ScrolledText(
            self, font=("Mono", 8), bg=BG2, fg=FG2,
            insertbackground=FG, relief="flat", padx=8, pady=6, wrap="none")
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
            low = line.lower()
            tag = ""
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
    def __init__(self, parent, row, label, svc, icon, port, log_cb, toggle_cb):
        self.svc      = svc
        self.label    = label
        self.port     = port
        self._log_cb  = log_cb
        self._tog_cb  = toggle_cb
        self._installed = True
        self._enabled_state = False

        col = 0

        # ── pulse dot
        self.dot = PulseDot(parent)
        self.dot.grid(row=row, column=col, padx=(8, 2), pady=7); col += 1

        # ── service name
        tk.Label(parent, text=f"{icon}  {label}", font=FONT_LABEL,
                 fg=FG, bg=PANEL, anchor="w", width=12)\
            .grid(row=row, column=col, sticky="w"); col += 1

        # ── status
        self.status_var = tk.StringVar(value="checking…")
        self.status_lbl = tk.Label(parent, textvariable=self.status_var,
                                   font=FONT_BOLD, fg=MUTED,
                                   bg=PANEL, anchor="w", width=11)
        self.status_lbl.grid(row=row, column=col, sticky="w", padx=2); col += 1

        # ── port indicator
        self.port_var = tk.StringVar(value="")
        self.port_lbl = tk.Label(parent, textvariable=self.port_var,
                                 font=FONT_SMALL, fg=MUTED,
                                 bg=PANEL, anchor="w", width=9)
        self.port_lbl.grid(row=row, column=col, sticky="w", padx=2); col += 1

        # ── uptime
        self.uptime_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.uptime_var,
                 font=FONT_SMALL, fg=MUTED, bg=PANEL, anchor="w", width=7)\
            .grid(row=row, column=col, sticky="w"); col += 1

        # ── CPU
        self.cpu_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.cpu_var,
                 font=FONT_SMALL, fg=PURPLE, bg=PANEL, anchor="w", width=6)\
            .grid(row=row, column=col, sticky="w"); col += 1

        # ── RAM
        self.ram_var = tk.StringVar(value="")
        tk.Label(parent, textvariable=self.ram_var,
                 font=FONT_SMALL, fg=CYAN, bg=PANEL, anchor="w", width=7)\
            .grid(row=row, column=col, sticky="w"); col += 1

        # ── autostart checkbox
        self.auto_var = tk.BooleanVar(value=False)
        self.auto_chk = tk.Checkbutton(
            parent, variable=self.auto_var,
            text="auto", font=FONT_SMALL,
            fg=MUTED, bg=PANEL, selectcolor=BG3,
            activebackground=PANEL, activeforeground=FG,
            command=self._on_toggle, cursor="hand2")
        self.auto_chk.grid(row=row, column=col, padx=4); col += 1

        # ── action buttons
        def mkbtn(text, cmd, w=7):
            return tk.Button(parent, text=text, command=cmd,
                             bg=BG3, fg=FG2, activebackground=ACCENT,
                             activeforeground=BG, relief="flat", bd=0,
                             padx=5, pady=3, font=("Sans", 9),
                             cursor="hand2", width=w)

        self.start_btn   = mkbtn("▶ start",   lambda: self.act("start"))
        self.stop_btn    = mkbtn("■ stop",    lambda: self.act("stop"))
        self.restart_btn = mkbtn("↺ restart", lambda: self.act("restart"))
        self.log_btn     = mkbtn("📋 logs",   lambda: self._log_cb(svc, label))

        self.start_btn.grid(row=row,   column=col,   padx=2); col += 1
        self.stop_btn.grid(row=row,    column=col,   padx=2); col += 1
        self.restart_btn.grid(row=row, column=col,   padx=2); col += 1
        self.log_btn.grid(row=row,     column=col,   padx=(2, 8))

        self._all_btns = [self.start_btn, self.stop_btn,
                          self.restart_btn, self.log_btn]

    def _on_toggle(self):
        want = self.auto_var.get()
        self._set_buttons(False)
        self.auto_chk.config(state="disabled")
        threading.Thread(target=self._do_toggle, args=(want,), daemon=True).start()

    def _do_toggle(self, want):
        self._tog_cb(self.svc, want)
        time.sleep(0.4)
        # re-read actual state
        actual = is_enabled(self.svc)
        self.auto_var.set(actual)
        self.auto_chk.config(
            fg=CYAN if actual else MUTED,
            state="normal")
        self._set_buttons(True)

    def act(self, action):
        self.status_var.set("working…")
        self.status_lbl.config(fg=WORKING)
        self.dot.set_color(WORKING, pulse=True)
        self._set_buttons(False)
        threading.Thread(target=self._run_action, args=(action,), daemon=True).start()

    def _run_action(self, action):
        subprocess.run(["pkexec", "systemctl", action, self.svc])
        time.sleep(0.7)
        self.refresh()
        self._set_buttons(True)

    def _set_buttons(self, enabled):
        state = "normal" if enabled else "disabled"
        for b in self._all_btns:
            b.config(state=state)

    def refresh(self):
        if not is_installed(self.svc):
            self._installed = False
            self.status_var.set("not installed")
            self.status_lbl.config(fg=DISABLED)
            self.dot.set_color(DISABLED, pulse=False)
            self.port_var.set("")
            self.uptime_var.set("")
            self.cpu_var.set("")
            self.ram_var.set("")
            self.auto_var.set(False)
            self.auto_chk.config(fg=MUTED, state="disabled")
            self._set_buttons(False)
            return

        self._installed = True
        active  = is_active(self.svc)
        enabled = is_enabled(self.svc)

        # status + dot
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

        # port check
        if self.port is not None:
            bound = port_bound(self.port)
            if bound:
                self.port_var.set(f":{self.port} ●")
                self.port_lbl.config(fg=RUNNING)
            else:
                self.port_var.set(f":{self.port} ○")
                self.port_lbl.config(fg=STOPPED if active else MUTED)
        else:
            self.port_var.set("")

        # cpu / ram
        if active:
            cpu, ram = get_cpu_ram(self.svc)
            self.cpu_var.set(cpu)
            self.ram_var.set(ram)
        else:
            self.cpu_var.set("—")
            self.ram_var.set("—")

        # autostart checkbox
        self.auto_var.set(enabled)
        self.auto_chk.config(
            fg=CYAN if enabled else MUTED,
            state="normal")

        self._set_buttons(True)


# ── FileZilla launcher row ────────────────────────────────────────────────────
class FileZillaRow:
    def __init__(self, parent, row):
        col = 0

        # dot placeholder (always cyan / ready)
        dot = tk.Canvas(parent, width=14, height=14, bg=PANEL,
                        highlightthickness=0)
        dot.create_oval(2, 2, 12, 12, fill=CYAN, outline="")
        dot.grid(row=row, column=col, padx=(8, 2), pady=7); col += 1

        tk.Label(parent, text="📂  FileZilla", font=FONT_LABEL,
                 fg=FG, bg=PANEL, anchor="w", width=12)\
            .grid(row=row, column=col, sticky="w"); col += 1

        self.status_var = tk.StringVar(value="launcher")
        tk.Label(parent, textvariable=self.status_var,
                 font=FONT_BOLD, fg=MUTED, bg=PANEL, anchor="w", width=11)\
            .grid(row=row, column=col, sticky="w", padx=2); col += 1

        # empty spacers for port / uptime / cpu / ram / checkbox columns
        for _ in range(5):
            tk.Label(parent, text="", bg=PANEL, width=6)\
                .grid(row=row, column=col); col += 1
        tk.Label(parent, text="", bg=PANEL, width=6)\
            .grid(row=row, column=col); col += 1  # checkbox col

        # open button spans where start/stop/restart would be
        open_btn = tk.Button(
            parent, text="📂 open FileZilla", command=self._launch,
            bg=BG3, fg=FG2, activebackground=PURPLE,
            activeforeground=BG, relief="flat", bd=0,
            padx=8, pady=3, font=("Sans", 9), cursor="hand2", width=22)
        open_btn.grid(row=row, column=col, columnspan=3, padx=2, sticky="w")
        col += 3

    def _launch(self):
        try:
            subprocess.Popen(["filezilla"])
            self.status_var.set("opening…")
        except FileNotFoundError:
            self.status_var.set("not installed")


# ── Main App ──────────────────────────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        root.title("Service Control Panel")
        root.configure(bg=BG)
        root.geometry("1020x460")
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
        headers = [
            ("",        2),  # dot
            ("service", 12), # name
            ("status",  11), # status
            ("port",    9),  # port
            ("uptime",  7),  # uptime
            ("cpu",     6),  # cpu
            ("ram",     7),  # ram
            ("boot",    6),  # checkbox
            ("",        7),  # start
            ("",        7),  # stop
            ("",        7),  # restart
            ("",        7),  # logs
        ]
        hrow = tk.Frame(root, bg=PANEL)
        hrow.pack(fill="x")
        for col, (text, w) in enumerate(headers):
            tk.Label(hrow, text=text.upper(), font=("Sans", 7), fg=MUTED,
                     bg=PANEL, width=w, anchor="w")\
                .grid(row=0, column=col,
                      padx=(8 if col == 0 else 2), pady=4, sticky="w")

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

        # ── service rows
        self.frame = tk.Frame(root, bg=PANEL)
        self.frame.pack(fill="both", expand=True)

        self.rows = []
        for i, (label, svc, icon, port) in enumerate(SERVICES):
            r = Row(self.frame, i, label, svc, icon, port,
                    self._open_logs, self._toggle_enabled)
            self.rows.append(r)

        # separator before FileZilla
        n = len(SERVICES)
        tk.Frame(self.frame, bg=BORDER, height=1)\
            .grid(row=n, column=0, columnspan=13, sticky="ew", padx=8, pady=2)

        FileZillaRow(self.frame, n + 1)

        # ── footer
        foot = tk.Frame(root, bg=BG2, pady=6)
        foot.pack(fill="x", side="bottom")
        self.summary_lbl = tk.Label(foot, text="", font=FONT_SMALL,
                                    fg=MUTED, bg=BG2)
        self.summary_lbl.pack(side="left", padx=16)
        tk.Button(foot, text="↻  Refresh All", command=self.refresh_all,
                  bg=BG3, fg=FG2, activebackground=ACCENT, activeforeground=BG,
                  relief="flat", bd=0, padx=10, pady=4,
                  font=("Sans", 9), cursor="hand2")\
            .pack(side="right", padx=12)

        self._auto_refresh()

    def _open_logs(self, svc, label):
        LogWindow(self.root, svc, label)

    def _toggle_enabled(self, svc, want):
        toggle_enabled(svc, want)

    def refresh_all(self):
        for r in self.rows:
            threading.Thread(target=r.refresh, daemon=True).start()
        self.root.after(900, self._update_summary)

    def _update_summary(self):
        installed = [r for r in self.rows if r._installed]
        running   = [r for r in installed if is_active(r.svc)]
        self.summary_lbl.config(
            text=f"{len(running)}/{len(installed)} services running  "
                 f"•  last refreshed {time.strftime('%H:%M:%S')}")

    def _auto_refresh(self):
        self.refresh_all()
        self.root.after(8000, self._auto_refresh)

    def _tick_clock(self):
        self.clock_lbl.config(text=time.strftime("  %A %d %b  %H:%M:%S  "))
        self.root.after(1000, self._tick_clock)


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()