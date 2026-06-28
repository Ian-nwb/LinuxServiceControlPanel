#!/usr/bin/env python3
import subprocess
import threading
import tkinter as tk
from tkinter import scrolledtext
import time
import socket

# ── Service definitions ───────────────────────────────────────────────────────
SERVICES = [
    ("MySQL",      "mysql",        "🐬", 3306),
    ("PostgreSQL", "postgresql",   "🐘", 5432),
    ("MongoDB",    "mongod",       "🍃", 27017),
    ("Redis",      "redis-server", "🔴", 6379),
    ("Valkey",     "valkey",       "🗝️",  6380),
    ("Docker",     "docker",       "🐳", None),
    ("Nginx",      "nginx",        "⚡", 80),
]

# App launchers: (label, icon, command, accent_color)
APP_LAUNCHERS = [
    ("FileZilla",  "📂", "filezilla",              "#7dcfff"),
    ("VS Code",    "🖊",  "code",                   "#7aa2f7"),
    ("Obsidian",   "🔮", "obsidian",               "#bb9af7"),
    ("Postman",    "📮", "postman",                 "#ff9e64"),
    ("Antigravity","🚀", "com.anticyclone.Antigravity", "#f7768e"),
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

FONT_LABEL = ("Sans", 10)
FONT_TITLE = ("Sans", 13, "bold")
FONT_SMALL = ("Mono", 8)
FONT_BOLD  = ("Mono", 9, "bold")

# ── Column layout (col index → pixel width for header labels) ─────────────────
# 0:dot 1:name 2:status 3:port 4:uptime 5:cpu 6:ram 7:chk 8:start 9:stop 10:restart 11:logs
COL_WIDTHS = [14, 110, 95, 80, 60, 50, 60, 52, 62, 55, 68, 55]


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

def toggle_enabled(svc, enable):
    subprocess.run(["pkexec", "systemctl", "enable" if enable else "disable", svc])

def port_bound(port):
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
    r = run(["systemctl", "show", svc,
             "--property=CPUUsageNSec",
             "--property=MemoryCurrent"])
    cpu_str = ram_str = "—"
    for line in r.stdout.splitlines():
        if line.startswith("MemoryCurrent="):
            try:
                b = int(line.split("=", 1)[1].strip())
                if b > 0:
                    ram_str = f"{b/1048576:.1f}M" if b < 1073741824 else f"{b/1073741824:.1f}G"
            except ValueError:
                pass
        elif line.startswith("CPUUsageNSec="):
            try:
                ns = int(line.split("=", 1)[1].strip())
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
    def __init__(self, parent, bg=PANEL):
        super().__init__(parent, width=14, height=14, bg=bg,
                         highlightthickness=0)
        self._color   = MUTED
        self._alpha   = 1.0
        self._dir     = -1
        self._pulsing = False
        self._dot     = self.create_oval(2, 2, 12, 12, fill=self._color, outline="")
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
                self.itemconfig(self._dot, fill=(
                    f"#{int(r/65535*self._alpha*255):02x}"
                    f"{int(g/65535*self._alpha*255):02x}"
                    f"{int(b/65535*self._alpha*255):02x}"))
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
            tag = ("err"  if any(w in low for w in ("error","failed","fatal","crit")) else
                   "warn" if any(w in low for w in ("warn","notice")) else
                   "ok"   if any(w in low for w in ("start","ready","success","listening")) else "")
            self.txt.insert("end", line + "\n", tag)
        self.txt.config(state="disabled")
        self.txt.see("end")


# ── Service row ───────────────────────────────────────────────────────────────
class Row:
    def __init__(self, parent, row, label, svc, icon, port, log_cb, toggle_cb):
        self.svc        = svc
        self.label      = label
        self.port       = port
        self._log_cb    = log_cb
        self._tog_cb    = toggle_cb
        self._installed = True

        def cell(col, widget):
            widget.grid(row=row, column=col, sticky="w",
                        padx=(6 if col == 0 else 2), pady=5)
            return widget

        # 0 dot
        self.dot = PulseDot(parent)
        cell(0, self.dot)

        # 1 name
        cell(1, tk.Label(parent, text=f"{icon}  {label}", font=FONT_LABEL,
                         fg=FG, bg=PANEL, anchor="w", width=11))

        # 2 status
        self.status_var = tk.StringVar(value="checking…")
        self.status_lbl = tk.Label(parent, textvariable=self.status_var,
                                   font=FONT_BOLD, fg=MUTED, bg=PANEL,
                                   anchor="w", width=10)
        cell(2, self.status_lbl)

        # 3 port
        self.port_var = tk.StringVar(value="")
        self.port_lbl = tk.Label(parent, textvariable=self.port_var,
                                 font=FONT_SMALL, fg=MUTED, bg=PANEL,
                                 anchor="w", width=9)
        cell(3, self.port_lbl)

        # 4 uptime
        self.uptime_var = tk.StringVar(value="")
        cell(4, tk.Label(parent, textvariable=self.uptime_var,
                         font=FONT_SMALL, fg=MUTED, bg=PANEL,
                         anchor="w", width=6))

        # 5 cpu
        self.cpu_var = tk.StringVar(value="")
        cell(5, tk.Label(parent, textvariable=self.cpu_var,
                         font=FONT_SMALL, fg=PURPLE, bg=PANEL,
                         anchor="w", width=5))

        # 6 ram
        self.ram_var = tk.StringVar(value="")
        cell(6, tk.Label(parent, textvariable=self.ram_var,
                         font=FONT_SMALL, fg=CYAN, bg=PANEL,
                         anchor="w", width=7))

        # 7 autostart checkbox  ← fixed: no text label, just the box + inline tag
        self.auto_var = tk.BooleanVar(value=False)
        self.auto_chk = tk.Checkbutton(
            parent, variable=self.auto_var, text="auto",
            font=("Sans", 8), fg=MUTED, bg=PANEL,
            selectcolor=BG3, activebackground=PANEL,
            activeforeground=FG, command=self._on_toggle, cursor="hand2",
            indicatoron=True, bd=0, highlightthickness=0)
        cell(7, self.auto_chk)

        # 8–11 action buttons
        def mkbtn(text, cmd):
            return tk.Button(parent, text=text, command=cmd,
                             bg=BG3, fg=FG2, activebackground=ACCENT,
                             activeforeground=BG, relief="flat", bd=0,
                             padx=5, pady=2, font=("Sans", 9), cursor="hand2")

        self.start_btn   = mkbtn("▶ start",   lambda: self.act("start"))
        self.stop_btn    = mkbtn("■ stop",    lambda: self.act("stop"))
        self.restart_btn = mkbtn("↺ restart", lambda: self.act("restart"))
        self.log_btn     = mkbtn("📋 logs",   lambda: self._log_cb(svc, label))

        for c, b in zip(range(8, 12),
                        [self.start_btn, self.stop_btn,
                         self.restart_btn, self.log_btn]):
            b.grid(row=row, column=c, padx=2, pady=5, sticky="w")

        self._all_btns = [self.start_btn, self.stop_btn,
                          self.restart_btn, self.log_btn]

    # ── checkbox toggle
    def _on_toggle(self):
        want = self.auto_var.get()
        self._set_buttons(False)
        self.auto_chk.config(state="disabled")
        threading.Thread(target=self._do_toggle, args=(want,), daemon=True).start()

    def _do_toggle(self, want):
        self._tog_cb(self.svc, want)
        time.sleep(0.4)
        actual = is_enabled(self.svc)
        self.auto_var.set(actual)
        self.auto_chk.config(fg=CYAN if actual else MUTED, state="normal")
        self._set_buttons(True)

    # ── service control
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

        if active:
            self.status_var.set("● running")
            self.status_lbl.config(fg=RUNNING)
            self.dot.set_color(RUNNING, pulse=True)
            self.uptime_var.set(get_uptime(self.svc))
            cpu, ram = get_cpu_ram(self.svc)
            self.cpu_var.set(cpu)
            self.ram_var.set(ram)
        else:
            self.status_var.set("○ stopped")
            self.status_lbl.config(fg=STOPPED)
            self.dot.set_color(STOPPED, pulse=False)
            self.uptime_var.set("")
            self.cpu_var.set("—")
            self.ram_var.set("—")

        if self.port is not None:
            bound = port_bound(self.port)
            self.port_var.set(f":{self.port} {'●' if bound else '○'}")
            self.port_lbl.config(fg=RUNNING if bound else (STOPPED if active else MUTED))
        else:
            self.port_var.set("")

        self.auto_var.set(enabled)
        self.auto_chk.config(fg=CYAN if enabled else MUTED, state="normal")
        self._set_buttons(True)


# ── App launcher strip ────────────────────────────────────────────────────────
class LauncherStrip:
    """A row of app-launch buttons sitting below the service list."""

    def __init__(self, parent, row):
        # thin separator
        tk.Frame(parent, bg=BORDER, height=1)\
            .grid(row=row, column=0, columnspan=13,
                  sticky="ew", padx=8, pady=(4, 2))

        strip = tk.Frame(parent, bg=PANEL)
        strip.grid(row=row + 1, column=0, columnspan=13,
                   sticky="ew", padx=8, pady=(2, 6))

        tk.Label(strip, text="apps", font=("Sans", 7), fg=MUTED,
                 bg=PANEL).pack(side="left", padx=(2, 8))

        self._labels = {}
        for label, icon, cmd, color in APP_LAUNCHERS:
            self._add_btn(strip, label, icon, cmd, color)

    def _add_btn(self, strip, label, icon, cmd, color):
        frame = tk.Frame(strip, bg=PANEL)
        frame.pack(side="left", padx=4)

        btn = tk.Button(
            frame, text=f"{icon}  {label}",
            command=lambda c=cmd, lbl=label: self._launch(c, lbl),
            bg=BG3, fg=FG2,
            activebackground=color, activeforeground=BG,
            relief="flat", bd=0, padx=8, pady=4,
            font=("Sans", 9), cursor="hand2")
        btn.pack()

        lbl_var = tk.StringVar(value="")
        lbl_w = tk.Label(frame, textvariable=lbl_var,
                         font=("Sans", 7), fg=MUTED, bg=PANEL)
        lbl_w.pack()
        self._labels[label] = lbl_var

    def _launch(self, cmd, label):
        def _run():
            try:
                # try plain name first, then flatpak
                result = subprocess.run(
                    ["which", cmd], capture_output=True, text=True)
                if result.returncode == 0:
                    subprocess.Popen([cmd])
                else:
                    # try as flatpak app id
                    subprocess.Popen(["flatpak", "run", cmd])
                self._labels[label].set("opening…")
            except FileNotFoundError:
                self._labels[label].set("not found")
            time.sleep(2)
            self._labels[label].set("")
        threading.Thread(target=_run, daemon=True).start()


# ── Main App ──────────────────────────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        root.title("Service Control Panel")
        root.configure(bg=BG)
        root.resizable(True, True)

        # ── header
        hdr = tk.Frame(root, bg=BG2, pady=8)
        hdr.pack(fill="x")
        tk.Label(hdr, text="⚙  Service Control Panel",
                 font=FONT_TITLE, fg=ACCENT, bg=BG2).pack(side="left", padx=14)
        self.clock_lbl = tk.Label(hdr, text="", font=FONT_SMALL, fg=MUTED, bg=BG2)
        self.clock_lbl.pack(side="right", padx=14)
        self._tick_clock()

        # ── column headers
        hrow = tk.Frame(root, bg=PANEL)
        hrow.pack(fill="x")
        headers = [
            ("",        0),
            ("service", 11),
            ("status",  10),
            ("port",    9),
            ("uptime",  6),
            ("cpu",     5),
            ("ram",     7),
            ("boot",    6),
            ("",        0), ("",0), ("",0), ("",0),
        ]
        for col, (text, w) in enumerate(headers):
            kw = dict(width=w) if w else {}
            tk.Label(hrow, text=text.upper(), font=("Sans", 7), fg=MUTED,
                     bg=PANEL, anchor="w", **kw)\
                .grid(row=0, column=col,
                      padx=(6 if col == 0 else 2), pady=3, sticky="w")

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x")

        # ── service rows
        self.frame = tk.Frame(root, bg=PANEL)
        self.frame.pack(fill="x")

        self.rows = []
        for i, (label, svc, icon, port) in enumerate(SERVICES):
            r = Row(self.frame, i, label, svc, icon, port,
                    self._open_logs, self._toggle_enabled)
            self.rows.append(r)

        # ── launcher strip
        n = len(SERVICES)
        LauncherStrip(self.frame, n)

        # ── footer
        foot = tk.Frame(root, bg=BG2, pady=5)
        foot.pack(fill="x", side="bottom")
        self.summary_lbl = tk.Label(foot, text="", font=FONT_SMALL,
                                    fg=MUTED, bg=BG2)
        self.summary_lbl.pack(side="left", padx=14)
        tk.Button(foot, text="↻  Refresh All", command=self.refresh_all,
                  bg=BG3, fg=FG2, activebackground=ACCENT, activeforeground=BG,
                  relief="flat", bd=0, padx=10, pady=3,
                  font=("Sans", 9), cursor="hand2")\
            .pack(side="right", padx=10)

        # size to content after first draw
        root.update_idletasks()
        root.minsize(root.winfo_reqwidth(), root.winfo_reqheight())
        root.geometry(f"{root.winfo_reqwidth()}x{root.winfo_reqheight()}")

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